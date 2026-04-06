"""Telegram bot for Impact News — onboarding, profiled delivery, feedback.

Handles:
- /start → ConversationHandler for user onboarding (segment 0)
- /profile → show current profile summary
- Inline keyboard callbacks for questionnaire + feedback
- Scheduled delivery jobs (HIGH push every 5min, daily digest at 8 AM)
"""

from __future__ import annotations

import datetime as dt
import json
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from profiling.engine import ProfileEngine
from profiling.diagnostics import DiagnosticsEngine
from pipeline.database import Database
from config import settings

logger = logging.getLogger(__name__)

# ConversationHandler states
CITY, WORK, TRANSPORT, HOUSING, FAMILY, DONE = range(6)

# Map question_id → ConversationHandler state
_QID_TO_STATE = {
    "s0_city": CITY,
    "s0_work": WORK,
    "s0_transport": TRANSPORT,
    "s0_housing": HOUSING,
    "s0_family": FAMILY,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_single_keyboard(question_id: str, options: list) -> InlineKeyboardMarkup:
    """Build inline keyboard for single_choice questions (2 per row)."""
    buttons = [
        InlineKeyboardButton(opt.label, callback_data=f"q|{question_id}|{opt.value}")
        for opt in options
    ]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


def _build_multi_keyboard(
    question_id: str, options: list, selected: set[str]
) -> InlineKeyboardMarkup:
    """Build inline keyboard for multi_choice with toggles and Done button."""
    buttons = []
    for opt in options:
        check = "\u2705 " if opt.value in selected else ""
        buttons.append(
            InlineKeyboardButton(
                f"{check}{opt.label}",
                callback_data=f"sel|{question_id}|{opt.value}",
            )
        )
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append(
        [InlineKeyboardButton("Done \u2713", callback_data=f"done|{question_id}")]
    )
    return InlineKeyboardMarkup(rows)


def _answer_emoji(question_id: str, value: str | list[str], engine: ProfileEngine) -> str:
    """Return a short display string for a confirmed answer."""
    emojis = {
        "s0_city": "\U0001f4cd",
        "s0_work": "\U0001f4bc",
        "s0_transport": "\U0001f697",
        "s0_housing": "\U0001f3e0",
        "s0_family": "\U0001f464",
    }
    icon = emojis.get(question_id, "\u2022")

    # Look up labels from engine
    q = engine._questions_by_id.get(question_id)
    if not q:
        return f"{icon} {value}"

    if question_id == "s0_city":
        return f"{icon} {value}"

    option_map = {opt.value: opt.label for opt in q.options}
    if isinstance(value, list):
        labels = [option_map.get(v, v) for v in value]
        return f"{icon} {', '.join(labels)}"
    return f"{icon} {option_map.get(value, value)}"


def _get_match_nodes(db: Database, match_id: int) -> list[str]:
    """Get matched node IDs from an article_matches record."""
    row = db.conn.execute(
        "SELECT matched_nodes_json FROM article_matches WHERE id = ?", (match_id,)
    ).fetchone()
    if not row or not row["matched_nodes_json"]:
        return []
    try:
        nodes = json.loads(row["matched_nodes_json"])
    except (json.JSONDecodeError, TypeError):
        return []
    return [n.get("node", "") for n in nodes if isinstance(n, dict) and n.get("node")]


def _get_depth_answers(db: Database, user_id: str) -> dict:
    """Load depth_answers from user profile (stored in raw_answers_json['_depth'])."""
    profile = db.get_user_profile(user_id)
    if not profile:
        return {}
    raw = profile.get("raw_answers_json", {})
    return raw.get("_depth", {})


def _save_depth_answers(db: Database, user_id: str, depth_answers: dict) -> None:
    """Persist depth_answers into raw_answers_json['_depth']."""
    profile = db.get_user_profile(user_id)
    if not profile:
        return
    raw = profile.get("raw_answers_json", {})
    raw["_depth"] = depth_answers
    db.conn.execute(
        "UPDATE user_profiles SET raw_answers_json = ?, updated_at = datetime('now') WHERE user_id = ?",
        (json.dumps(raw), user_id),
    )
    db.conn.commit()


def _get_feedback_count(db: Database, user_id: str) -> int:
    """Count total feedback events for a user."""
    row = db.conn.execute(
        "SELECT COUNT(*) as cnt FROM profile_feedback_log WHERE user_id = ?", (user_id,)
    ).fetchone()
    return row["cnt"] if row else 0


def _apply_adjustments(db: Database, user_id: str, adjustments: dict[str, float]) -> None:
    """Apply node weight deltas to user profile."""
    if not adjustments:
        return
    profile = db.get_user_profile(user_id)
    if not profile:
        return
    weights = profile.get("node_weights_json", {})
    for node, delta in adjustments.items():
        weights[node] = weights.get(node, 0.0) + delta
    db.update_user_weights(user_id, weights)


# ---------------------------------------------------------------------------
# /start → onboarding ConversationHandler
# ---------------------------------------------------------------------------


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start — check for existing profile or begin onboarding."""
    chat_id = str(update.effective_chat.id)
    db: Database = context.bot_data["db"]

    profile = db.get_user_profile(chat_id)
    if profile:
        await update.message.reply_text(
            "Welcome back! Your profile is active.\nUse /profile to see it."
        )
        return ConversationHandler.END

    # Initialize onboarding state
    context.user_data["answers"] = {}
    context.user_data["selections"] = set()

    await update.message.reply_text(
        "Welcome to Impact News! \U0001f4f0\n\n"
        "I'll ask 5 quick questions to personalize your news.\n"
        "Let's start — which city do you live in?"
    )
    return CITY


async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle city text input, then ask work question."""
    city = update.message.text.strip()
    context.user_data["answers"]["s0_city"] = city

    engine: ProfileEngine = context.bot_data["engine"]
    tier, state, _ = engine.resolve_city(city)
    tier_label = {"metro": "metro", "tier2": "tier-2", "rural": "rural"}.get(tier, tier)

    await update.message.reply_text(f"\U0001f4cd {city} ({tier_label})")

    # Ask work question
    q = engine._questions_by_id["s0_work"]
    keyboard = _build_single_keyboard(q.id, q.options)
    await update.message.reply_text(q.text, reply_markup=keyboard)
    return WORK


async def handle_single_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle single_choice callback for work/housing questions."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")
    if len(parts) != 3:
        return None
    _, question_id, value = parts

    context.user_data["answers"][question_id] = value
    engine: ProfileEngine = context.bot_data["engine"]

    # Confirm selection
    label = _answer_emoji(question_id, value, engine)
    await query.edit_message_text(f"{query.message.text}\n\n{label}")

    # Advance to next state
    if question_id == "s0_work":
        q = engine._questions_by_id["s0_transport"]
        context.user_data["selections"] = set()
        keyboard = _build_multi_keyboard(q.id, q.options, set())
        await query.message.reply_text(q.text, reply_markup=keyboard)
        return TRANSPORT
    elif question_id == "s0_housing":
        q = engine._questions_by_id["s0_family"]
        context.user_data["selections"] = set()
        keyboard = _build_multi_keyboard(q.id, q.options, set())
        await query.message.reply_text(q.text, reply_markup=keyboard)
        return FAMILY

    return None


async def handle_multi_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """Handle sel| toggle for multi_choice questions."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")
    if len(parts) != 3:
        return None
    _, question_id, value = parts

    selected: set = context.user_data.get("selections", set())

    if value in selected:
        selected.discard(value)
    else:
        selected.add(value)
    context.user_data["selections"] = selected

    engine: ProfileEngine = context.bot_data["engine"]
    q = engine._questions_by_id.get(question_id)
    if not q:
        return None

    keyboard = _build_multi_keyboard(q.id, q.options, selected)
    await query.edit_message_reply_markup(reply_markup=keyboard)
    return None  # stay in same state


async def handle_multi_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle done| callback for multi_choice — commit selections, advance."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")
    if len(parts) != 2:
        return None
    _, question_id = parts

    selected = list(context.user_data.get("selections", set()))
    if not selected:
        await query.answer("Please select at least one option.", show_alert=True)
        return None

    context.user_data["answers"][question_id] = selected
    engine: ProfileEngine = context.bot_data["engine"]

    # Confirm selection
    label = _answer_emoji(question_id, selected, engine)
    await query.edit_message_text(f"{query.message.text}\n\n{label}")

    # Advance
    if question_id == "s0_transport":
        q = engine._questions_by_id["s0_housing"]
        keyboard = _build_single_keyboard(q.id, q.options)
        await query.message.reply_text(q.text, reply_markup=keyboard)
        return HOUSING
    elif question_id == "s0_family":
        return await _finish_onboarding(query, context)

    return None


async def _finish_onboarding(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Compute profile, save to DB, send confirmation."""
    chat_id = str(query.message.chat.id)
    raw_answers = context.user_data["answers"]
    engine: ProfileEngine = context.bot_data["engine"]
    db: Database = context.bot_data["db"]

    # Compute profile
    profile = engine.compute_profile(raw_answers)
    tier, state, _ = engine.resolve_city(str(raw_answers.get("s0_city", "")))

    db.save_user_profile(
        user_id=chat_id,
        chat_id=chat_id,
        city=raw_answers.get("s0_city", ""),
        city_tier=tier,
        raw_answers=raw_answers,
        node_weights=profile,
        completed_segments=[0],
    )

    # Build confirmation
    tier_label = {"metro": "metro", "tier2": "tier-2", "rural": "rural"}.get(tier, tier)
    lines = ["\u2705 Profile set up!\n"]
    lines.append(_answer_emoji("s0_city", f"{raw_answers.get('s0_city', '')} ({tier_label})", engine))
    lines.append(_answer_emoji("s0_work", raw_answers.get("s0_work", ""), engine))
    lines.append(
        _answer_emoji("s0_transport", raw_answers.get("s0_transport", []), engine)
    )
    lines.append(_answer_emoji("s0_housing", raw_answers.get("s0_housing", ""), engine))
    lines.append(_answer_emoji("s0_family", raw_answers.get("s0_family", []), engine))
    lines.append(f"\n{len(profile)} impact nodes active. You'll start receiving personalized news!")

    await query.message.reply_text("\n".join(lines))
    logger.info("Onboarding complete: user=%s nodes=%d", chat_id, len(profile))

    # Cleanup
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel during onboarding."""
    context.user_data.clear()
    await update.message.reply_text("Onboarding cancelled. Send /start to try again.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /profile command
# ---------------------------------------------------------------------------


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current user profile summary."""
    chat_id = str(update.effective_chat.id)
    db: Database = context.bot_data["db"]

    profile = db.get_user_profile(chat_id)
    if not profile:
        await update.message.reply_text("No profile found. Send /start to set one up.")
        return

    city = profile.get("city", "Unknown")
    city_tier = profile.get("city_tier", "")
    tier_label = {"metro": "metro", "tier2": "tier-2", "rural": "rural"}.get(city_tier, city_tier)
    weights = profile.get("node_weights_json", {})
    segments = profile.get("completed_segments", [])

    # Top nodes by weight
    top = sorted(weights.items(), key=lambda x: -x[1])[:8]
    top_lines = "\n".join(f"  \u2022 {node}: {w:.1f}" for node, w in top)

    text = (
        f"\U0001f4ca Your Profile\n\n"
        f"City: {city} ({tier_label})\n"
        f"Nodes: {len(weights)} active\n"
        f"Segments: {len(segments)} complete\n\n"
        f"Top nodes:\n{top_lines}"
    )
    await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# Message formatting & delivery
# ---------------------------------------------------------------------------


def format_impact_message(match: dict) -> str:
    """Format an article match for Telegram delivery."""
    severity = match.get("severity", "low")
    severity_emoji = {"high": "\U0001f534", "medium": "\U0001f7e1", "low": "\U0001f7e2"}.get(
        severity, "\U0001f7e2"
    )
    severity_label = {"high": "PUSH", "medium": "DIGEST", "low": "LOW"}.get(severity, "LOW")

    title = match.get("title", "Untitled")
    source = match.get("source", "Unknown")
    url = match.get("url", "")
    score = match.get("score", 0)

    # Parse matched_nodes
    matched_nodes = match.get("matched_nodes_json")
    if isinstance(matched_nodes, str):
        try:
            matched_nodes = json.loads(matched_nodes)
        except (json.JSONDecodeError, TypeError):
            matched_nodes = []
    if not matched_nodes:
        matched_nodes = []

    lines = [
        f"{severity_emoji} {severity_label} | Score: {score:.2f}",
        "",
        f"*{title}*",
        f"_{source}_",
    ]

    # Why this affects you
    if matched_nodes:
        lines.append("")
        lines.append("\U0001f4a1 *Why this affects you:*")
        for node in matched_nodes[:3]:
            node_id = node.get("node", "?")
            rationale = node.get("rationale", "")
            if rationale:
                lines.append(f"\u2022 {node_id} \u2014 {rationale}")
            else:
                lines.append(f"\u2022 {node_id}")

    if url:
        lines.append("")
        lines.append(f"\U0001f517 [Read Full Article]({url})")

    return "\n".join(lines)


def build_feedback_keyboard(match_id: int) -> InlineKeyboardMarkup:
    """Build feedback buttons for a delivered article."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "\U0001f44d Relevant", callback_data=f"fb|{match_id}|rel"
                ),
                InlineKeyboardButton(
                    "\U0001f44e Not Relevant", callback_data=f"fb|{match_id}|not"
                ),
            ]
        ]
    )


# ---------------------------------------------------------------------------
# Callback handlers
# ---------------------------------------------------------------------------


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle feedback button callbacks (fb|{match_id}|{type}).

    On thumbs-down: present a diagnostic question if available.
    On thumbs-up: occasionally present a deepening question.
    """
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")
    if len(parts) != 3:
        return

    _, match_id_str, feedback_type = parts
    try:
        match_id = int(match_id_str)
    except ValueError:
        return

    db: Database = context.bot_data.get("db")
    if db is None:
        return

    feedback_map = {"rel": "relevant", "not": "not_relevant"}
    fb = feedback_map.get(feedback_type, feedback_type)
    db.save_feedback(match_id, fb)
    await query.edit_message_reply_markup(reply_markup=None)

    user_id = str(update.effective_chat.id)
    diagnostics: DiagnosticsEngine | None = context.bot_data.get("diagnostics")

    if feedback_type == "not" and diagnostics:
        try:
            matched_nodes = _get_match_nodes(db, match_id)
            depth_answers = _get_depth_answers(db, user_id)
            diag = diagnostics.select_diagnostic(matched_nodes, depth_answers)
            if diag:
                buttons = [
                    [InlineKeyboardButton(
                        opt.label,
                        callback_data=f"diag|{match_id}|{diag.id}|{i}",
                    )]
                    for i, opt in enumerate(diag.options)
                ]
                await query.message.reply_text(
                    f"\U0001f44e {diag.text}",
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                db.append_feedback_log(user_id, match_id, fb)
                logger.info("Feedback: match=%d type=%s diag=%s", match_id, fb, diag.id)
                return
        except Exception:
            logger.exception("Diagnostic selection failed for match=%d", match_id)

    elif feedback_type == "rel" and diagnostics:
        try:
            matched_nodes = _get_match_nodes(db, match_id)
            depth_answers = _get_depth_answers(db, user_id)
            feedback_count = _get_feedback_count(db, user_id)
            deep = diagnostics.select_deepening(matched_nodes, depth_answers, feedback_count)
            if deep:
                buttons = [
                    [InlineKeyboardButton(
                        opt.label,
                        callback_data=f"deep|{match_id}|{deep.id}|{i}",
                    )]
                    for i, opt in enumerate(deep.options)
                ]
                await query.message.reply_text(
                    f"\U0001f44d {deep.text}",
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                db.append_feedback_log(user_id, match_id, fb)
                logger.info("Feedback: match=%d type=%s deep=%s", match_id, fb, deep.id)
                return
        except Exception:
            logger.exception("Deepening selection failed for match=%d", match_id)

    # Fallback: simple confirmation
    emoji = "\U0001f44d" if feedback_type == "rel" else "\U0001f44e"
    await query.message.reply_text(f"{emoji} Feedback saved. Thanks!")
    db.append_feedback_log(user_id, match_id, fb)
    logger.info("Feedback: match=%d type=%s", match_id, fb)


async def handle_diagnostic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle diagnostic option selection (diag|{match_id}|{diag_id}|{option_index})."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")
    if len(parts) != 4:
        return

    _, match_id_str, diag_id, opt_idx_str = parts
    try:
        match_id = int(match_id_str)
        opt_idx = int(opt_idx_str)
    except ValueError:
        return

    db: Database = context.bot_data.get("db")
    diagnostics: DiagnosticsEngine | None = context.bot_data.get("diagnostics")
    if not db or not diagnostics:
        return

    user_id = str(update.effective_chat.id)

    # Look up the question and option
    diag = next((d for d in diagnostics.diagnostics if d.id == diag_id), None)
    if not diag or opt_idx >= len(diag.options):
        await query.edit_message_text("Got it, thanks!")
        return

    opt = diag.options[opt_idx]
    await query.edit_message_reply_markup(reply_markup=None)

    # Apply depth_update
    if opt.depth_update:
        depth_answers = _get_depth_answers(db, user_id)
        depth_answers.update(opt.depth_update)
        _save_depth_answers(db, user_id, depth_answers)

    # Apply weight adjustments
    if opt.adjustments:
        _apply_adjustments(db, user_id, opt.adjustments)

    # Log
    db.append_feedback_log(
        user_id, match_id, "diagnostic",
        diagnostic_question_id=diag_id,
        diagnostic_answer=opt.label,
        node_adjustments=opt.adjustments or None,
    )

    # Handle action
    if opt.action == "follow_up" and opt.follow_up_id:
        depth_q = diagnostics.get_depth_question(opt.follow_up_id)
        if depth_q:
            buttons = [
                [InlineKeyboardButton(
                    dopt.label,
                    callback_data=f"depth|{match_id}|{depth_q.id}|{i}",
                )]
                for i, dopt in enumerate(depth_q.options)
            ]
            await query.message.reply_text(
                depth_q.text,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return

    if opt.action == "flag_location":
        await query.message.reply_text("Thanks! We'll improve location matching.")
        return

    await query.message.reply_text("Got it, we'll tune your feed!")


async def handle_depth_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle depth follow-up answer (depth|{match_id}|{depth_id}|{option_index})."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")
    if len(parts) != 4:
        return

    _, match_id_str, depth_id, opt_idx_str = parts
    try:
        match_id = int(match_id_str)
        opt_idx = int(opt_idx_str)
    except ValueError:
        return

    db: Database = context.bot_data.get("db")
    diagnostics: DiagnosticsEngine | None = context.bot_data.get("diagnostics")
    if not db or not diagnostics:
        return

    user_id = str(update.effective_chat.id)
    depth_q = diagnostics.get_depth_question(depth_id)
    if not depth_q or opt_idx >= len(depth_q.options):
        await query.edit_message_text("Profile updated!")
        return

    opt = depth_q.options[opt_idx]
    await query.edit_message_reply_markup(reply_markup=None)

    # Apply depth_update
    if opt.depth_update:
        depth_answers = _get_depth_answers(db, user_id)
        depth_answers.update(opt.depth_update)
        _save_depth_answers(db, user_id, depth_answers)

    # Apply weight adjustments
    if opt.adjustments:
        _apply_adjustments(db, user_id, opt.adjustments)

    # Log
    db.append_feedback_log(
        user_id, match_id, "depth_answer",
        depth_question_id=depth_id,
        depth_answer=opt.label,
        node_adjustments=opt.adjustments or None,
    )

    await query.message.reply_text("Profile updated! Your feed will be more precise.")


async def handle_deepening_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle deepening question answer (deep|{match_id}|{deep_id}|{option_index})."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")
    if len(parts) != 4:
        return

    _, match_id_str, deep_id, opt_idx_str = parts
    try:
        match_id = int(match_id_str)
        opt_idx = int(opt_idx_str)
    except ValueError:
        return

    db: Database = context.bot_data.get("db")
    diagnostics: DiagnosticsEngine | None = context.bot_data.get("diagnostics")
    if not db or not diagnostics:
        return

    user_id = str(update.effective_chat.id)
    deep = next((d for d in diagnostics.deepening if d.id == deep_id), None)
    if not deep or opt_idx >= len(deep.options):
        await query.edit_message_text("Profile updated!")
        return

    opt = deep.options[opt_idx]
    await query.edit_message_reply_markup(reply_markup=None)

    # Apply depth_update
    if opt.depth_update:
        depth_answers = _get_depth_answers(db, user_id)
        depth_answers.update(opt.depth_update)
        _save_depth_answers(db, user_id, depth_answers)

    # Apply weight adjustments
    if opt.adjustments:
        _apply_adjustments(db, user_id, opt.adjustments)

    # Log
    db.append_feedback_log(
        user_id, match_id, "deepening_answer",
        diagnostic_question_id=deep_id,
        diagnostic_answer=opt.label,
        node_adjustments=opt.adjustments or None,
    )

    await query.message.reply_text("Profile updated! Your feed will be more precise.")


# ---------------------------------------------------------------------------
# Delivery jobs
# ---------------------------------------------------------------------------


async def _deliver_matches(
    context: ContextTypes.DEFAULT_TYPE, user_id: str, chat_id: str, matches: list[dict]
) -> int:
    """Send matches to a chat. Returns count delivered."""
    db: Database = context.bot_data["db"]
    sent = 0
    for match in matches:
        text = format_impact_message(match)
        keyboard = build_feedback_keyboard(match["id"])
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
                reply_markup=keyboard,
            )
            db.mark_delivered(match["id"])
            sent += 1
        except Exception:
            logger.exception("Failed to deliver match %d to %s", match["id"], chat_id)
    return sent


async def check_high_priority(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: push HIGH severity matches immediately."""
    db: Database = context.bot_data.get("db")
    if not db:
        return

    user_ids = db.get_all_user_ids()
    if not user_ids:
        # Fallback: deliver to settings chat_id if no profiles yet
        chat_id = settings.telegram_chat_id
        if chat_id:
            deliveries = db.get_pending_deliveries("default", min_severity="high")
            if deliveries:
                await _deliver_matches(context, "default", chat_id, deliveries)
        return

    for user_id in user_ids:
        profile = db.get_user_profile(user_id)
        if not profile:
            continue
        chat_id = profile["telegram_chat_id"]
        deliveries = db.get_pending_deliveries(user_id, min_severity="high")
        if deliveries:
            n = await _deliver_matches(context, user_id, chat_id, deliveries)
            logger.info("Delivered %d HIGH matches to user=%s", n, user_id)


async def send_daily_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: compile MEDIUM matches into daily digest."""
    db: Database = context.bot_data.get("db")
    if not db:
        return

    user_ids = db.get_all_user_ids()
    if not user_ids:
        chat_id = settings.telegram_chat_id
        if chat_id:
            deliveries = db.get_pending_deliveries("default", min_severity="medium")
            medium = [d for d in deliveries if d.get("severity") == "medium"]
            if medium:
                await _deliver_matches(context, "default", chat_id, medium[:10])
        return

    for user_id in user_ids:
        profile = db.get_user_profile(user_id)
        if not profile:
            continue
        chat_id = profile["telegram_chat_id"]
        deliveries = db.get_pending_deliveries(user_id, min_severity="medium")
        medium = [d for d in deliveries if d.get("severity") == "medium"]
        if medium:
            n = await _deliver_matches(context, user_id, chat_id, medium[:10])
            logger.info("Daily digest: %d medium matches to user=%s", n, user_id)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(db: Database | None = None) -> None:
    """Start the bot with optional shared pipeline state."""
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Shared state
    if not db:
        db = Database(settings.db_path)
        db.init_schema()
    app.bot_data["db"] = db
    app.bot_data["engine"] = ProfileEngine()
    app.bot_data["diagnostics"] = DiagnosticsEngine()

    # Onboarding conversation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city)],
            WORK: [CallbackQueryHandler(handle_single_choice, pattern=r"^q\|s0_work\|")],
            TRANSPORT: [
                CallbackQueryHandler(handle_multi_toggle, pattern=r"^sel\|s0_transport\|"),
                CallbackQueryHandler(handle_multi_done, pattern=r"^done\|s0_transport$"),
            ],
            HOUSING: [CallbackQueryHandler(handle_single_choice, pattern=r"^q\|s0_housing\|")],
            FAMILY: [
                CallbackQueryHandler(handle_multi_toggle, pattern=r"^sel\|s0_family\|"),
                CallbackQueryHandler(handle_multi_done, pattern=r"^done\|s0_family$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    app.add_handler(conv_handler)

    # Profile command
    app.add_handler(CommandHandler("profile", profile_command))

    # Feedback handler (outside conversation)
    app.add_handler(CallbackQueryHandler(handle_feedback, pattern=r"^fb\|"))
    app.add_handler(CallbackQueryHandler(handle_diagnostic, pattern=r"^diag\|"))
    app.add_handler(CallbackQueryHandler(handle_depth_answer, pattern=r"^depth\|"))
    app.add_handler(CallbackQueryHandler(handle_deepening_answer, pattern=r"^deep\|"))

    # Delivery jobs
    job_queue = app.job_queue
    job_queue.run_repeating(check_high_priority, interval=300, first=10)
    job_queue.run_daily(
        send_daily_digest,
        time=dt.time(settings.digest_hour, 0),
    )
    logger.info(
        "Delivery jobs registered: HIGH every 5min, digest at %d:00",
        settings.digest_hour,
    )

    print("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
