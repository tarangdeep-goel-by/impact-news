"""Telegram bot for Impact News onboarding and interaction."""

import datetime as dt
import json
import logging
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
)

from user.onboarding import QUESTIONS, EXCLUSIVE_OPTIONS, normalize_answer
from user.inference import connect_user_to_graph
from graph.graph import ImpactGraph
from models import UserGraph
from pipeline.database import Database
from config import settings

logger = logging.getLogger(__name__)

# Conversation states
(CITY, WORK_SECTOR, HOUSING, COMMUTE, LOANS, INVESTMENTS, DIET, DEPENDENTS, HEALTH) = range(9)


def build_keyboard(question, selected=None):
    """Build inline keyboard for a question."""
    selected = selected or []
    buttons = []
    row = []
    for i, option in enumerate(question.options):
        label = f"\u2713 {option}" if option in selected else option
        callback = f"{question.callback_prefix}:{option}"
        row.append(InlineKeyboardButton(label, callback_data=callback))
        if len(row) == 3 or i == len(question.options) - 1:
            buttons.append(row)
            row = []
    if question.multi_select:
        buttons.append([InlineKeyboardButton("\u2705 Done", callback_data=f"{question.callback_prefix}:DONE")])
    return InlineKeyboardMarkup(buttons)


async def send_question(update, context, q_index):
    """Send question q_index to the user."""
    question = QUESTIONS[q_index]
    filled = "\u25cf" * (q_index + 1)
    remaining = "\u25cb" * (9 - q_index - 1)
    text = f"Question {q_index + 1}/9  {filled}{remaining}\n\n{question.text}"
    keyboard = build_keyboard(question)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start and /profile commands."""
    context.user_data["answers"] = {}
    context.user_data["multi_selections"] = []
    await send_question(update, context, 0)
    return CITY


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle all inline keyboard callbacks during onboarding."""
    query = update.callback_query
    await query.answer()

    data = query.data
    prefix, value = data.split(":", 1)

    # Find current question index by prefix
    q_index = next(i for i, q in enumerate(QUESTIONS) if q.callback_prefix == prefix)
    question = QUESTIONS[q_index]

    if question.multi_select:
        if value == "DONE":
            # Save multi-select answers
            selections = context.user_data.get("multi_selections", [])
            answer_values = [normalize_answer(s) for s in selections]
            context.user_data["answers"][question.key] = answer_values
            context.user_data["multi_selections"] = []
        else:
            # Toggle selection
            selections = context.user_data.get("multi_selections", [])

            if value in EXCLUSIVE_OPTIONS:
                # Exclusive option: clear everything else, keep only this
                if value in selections:
                    selections.remove(value)
                else:
                    selections = [value]
            else:
                # Regular option: remove any exclusive options, then toggle
                selections = [s for s in selections if s not in EXCLUSIVE_OPTIONS]
                if value in selections:
                    selections.remove(value)
                else:
                    selections.append(value)

            context.user_data["multi_selections"] = selections
            # Redraw keyboard with updated selections
            keyboard = build_keyboard(question, selected=selections)
            filled = "\u25cf" * (q_index + 1)
            remaining = "\u25cb" * (9 - q_index - 1)
            text = f"Question {q_index + 1}/9  {filled}{remaining}\n\n{question.text}"
            await query.edit_message_text(text, reply_markup=keyboard)
            return q_index  # Stay on same question
    else:
        # Single select
        context.user_data["answers"][question.key] = normalize_answer(value)

    # Advance to next question or finish
    next_index = q_index + 1
    if next_index < len(QUESTIONS):
        await send_question(update, context, next_index)
        return next_index
    else:
        return await finish_onboarding(update, context)


async def finish_onboarding(update, context) -> int:
    """Compute user graph, save it, and show summary."""
    answers = context.user_data["answers"]
    user_id = str(update.effective_user.id)

    graph = context.bot_data.get("graph")
    if graph is None:
        graph = ImpactGraph(settings.graph_path)
        graph.load()
    user_graph = connect_user_to_graph(answers, graph, user_id=user_id)

    # Save to file
    Path("data").mkdir(exist_ok=True)
    with open("data/user_graph.json", "w") as f:
        json.dump(user_graph.model_dump(mode="json"), f, indent=2, default=list)

    summary = (
        f"Profile complete!\n\n"
        f"Direct connections: {len(user_graph.edges)} nodes\n"
        f"Reachable impact zone: {len(user_graph.reachable_nodes)} nodes\n\n"
        f"I'll track news that affects these areas of your life.\n"
        f"Use /profile to update your answers anytime."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(summary)
    else:
        await update.message.reply_text(summary)

    return ConversationHandler.END


# --- Message Formatting & Delivery ---

def format_impact_message(match: dict) -> str:
    """Format an impact match for Telegram delivery."""
    severity = match.get("severity", "low")
    severity_emoji = {"high": "\U0001f534", "medium": "\U0001f7e1", "low": "\U0001f7e2"}.get(severity, "\U0001f7e2")
    severity_label = severity.upper()

    title = match.get("title", "Untitled")
    source = match.get("source", "Unknown")
    url = match.get("url", "")
    explanation = match.get("explanation", "")
    score = match.get("score", 0)

    # Build impact chain from matched nodes
    matched_nodes = match.get("matched_nodes_json")
    if isinstance(matched_nodes, str):
        try:
            matched_nodes = json.loads(matched_nodes)
        except (json.JSONDecodeError, TypeError):
            matched_nodes = []
    if not matched_nodes:
        matched_nodes = []

    chain_parts = []
    for node in matched_nodes[:3]:
        path = node.get("path", [])
        if path:
            chain_parts.append(" \u2192 ".join(path[-3:]))

    chain_str = "\n".join(f"  \u2022 {c}" for c in chain_parts) if chain_parts else ""

    polarity = matched_nodes[0].get("polarity", 0) if matched_nodes else 0
    polarity_sym = {1: "\u2191", -1: "\u2193", 0: "~"}.get(polarity, "~")
    delay = matched_nodes[0].get("delay", "") if matched_nodes else ""

    lines = [
        f"{severity_emoji} *{severity_label} IMPACT*",
        "",
        f"*{title}*",
        f"_{source}_",
    ]

    if explanation:
        lines += ["", f"\U0001f4a1 *Why this matters to you:*", explanation]

    if chain_str:
        lines += ["", f"\U0001f4ca *Impact chain:*", chain_str]

    lines += [
        "",
        f"Score: {score:.2f} | Polarity: {polarity_sym} | Timeline: {delay}",
    ]

    if url:
        lines += ["", f"\U0001f517 [Read Full Article]({url})"]

    return "\n".join(lines)


def build_feedback_keyboard(match_id: int) -> InlineKeyboardMarkup:
    """Build feedback buttons for a delivered article."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\U0001f44d Relevant", callback_data=f"fb|{match_id}|rel"),
            InlineKeyboardButton("\U0001f44e Not Relevant", callback_data=f"fb|{match_id}|not"),
        ]
    ])


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle feedback button callbacks (fb|{match_id}|{type})."""
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

    emoji = "\U0001f44d" if feedback_type == "rel" else "\U0001f44e"
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"{emoji} Feedback saved. Thanks!")
    logger.info("Feedback: match=%d type=%s", match_id, fb)


async def check_high_priority(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: check for HIGH severity matches, push immediately."""
    db: Database = context.bot_data.get("db")
    chat_id = settings.telegram_chat_id
    if not db or not chat_id:
        return

    user_graph: UserGraph = context.bot_data.get("user_graph")
    if not user_graph:
        return

    deliveries = db.get_pending_deliveries(user_graph.user_id, min_severity="high")
    for match in deliveries:
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
            logger.info("Delivered HIGH: match=%d article=%s", match["id"], match["article_id"][:12])
        except Exception:
            logger.exception("Failed to deliver match %d", match["id"])


async def send_daily_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: compile MEDIUM matches into daily digest at 8 AM."""
    db: Database = context.bot_data.get("db")
    chat_id = settings.telegram_chat_id
    if not db or not chat_id:
        return

    user_graph: UserGraph = context.bot_data.get("user_graph")
    if not user_graph:
        return

    deliveries = db.get_pending_deliveries(user_graph.user_id, min_severity="medium")
    # Filter out HIGH (already pushed) — only MEDIUM
    medium = [d for d in deliveries if d.get("severity") == "medium"]

    if not medium:
        return

    header = f"\U0001f4f0 *Daily Impact Digest* — {len(medium)} articles\n"
    messages = [header]

    for match in medium[:10]:  # Cap at 10 per digest
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
        except Exception:
            logger.exception("Failed to deliver digest match %d", match["id"])

    logger.info("Daily digest sent: %d medium matches", len(medium))


def main(
    db: Database | None = None,
    graph: ImpactGraph | None = None,
    node_matcher=None,
    user_graph: UserGraph | None = None,
    gemini=None,
) -> None:
    """Start the bot with optional shared pipeline state."""
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Store shared state in bot_data
    if db:
        app.bot_data["db"] = db
    if graph:
        app.bot_data["graph"] = graph
    if node_matcher:
        app.bot_data["matcher"] = node_matcher
    if user_graph:
        app.bot_data["user_graph"] = user_graph
    if gemini:
        app.bot_data["gemini"] = gemini

    # Onboarding conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("profile", start),
        ],
        states={i: [CallbackQueryHandler(handle_answer)] for i in range(9)},
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(conv_handler)

    # Feedback handler (separate from onboarding callbacks)
    app.add_handler(CallbackQueryHandler(handle_feedback, pattern=r"^fb\|"))

    # Delivery jobs (only if db + user_graph available)
    if db and user_graph:
        job_queue = app.job_queue
        # Check for HIGH priority every 5 minutes
        job_queue.run_repeating(check_high_priority, interval=300, first=10)
        # Daily digest at configured hour
        job_queue.run_daily(
            send_daily_digest,
            time=dt.time(settings.digest_hour, 0),
        )
        logger.info("Delivery jobs registered: HIGH every 5min, digest at %d:00", settings.digest_hour)

    print("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
