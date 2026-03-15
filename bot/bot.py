"""Telegram bot for Impact News — delivery and feedback.

Onboarding and user profiling will be rebuilt for the new graph.
Currently supports: message delivery, feedback collection.
"""

import datetime as dt
import json
import logging
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
)

from pipeline.database import Database
from config import settings

logger = logging.getLogger(__name__)


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

    user_id = context.bot_data.get("user_id", "default")
    deliveries = db.get_pending_deliveries(user_id, min_severity="high")
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

    user_id = context.bot_data.get("user_id", "default")
    deliveries = db.get_pending_deliveries(user_id, min_severity="medium")
    # Filter out HIGH (already pushed) — only MEDIUM
    medium = [d for d in deliveries if d.get("severity") == "medium"]

    if not medium:
        return

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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(
    db: Database | None = None,
    graph: ImpactGraph | None = None,
    node_matcher=None,
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
    if gemini:
        app.bot_data["gemini"] = gemini

    # Feedback handler
    app.add_handler(CallbackQueryHandler(handle_feedback, pattern=r"^fb\|"))

    # Delivery jobs (only if db available)
    if db:
        job_queue = app.job_queue
        job_queue.run_repeating(check_high_priority, interval=300, first=10)
        job_queue.run_daily(
            send_daily_digest,
            time=dt.time(settings.digest_hour, 0),
        )
        logger.info("Delivery jobs registered: HIGH every 5min, digest at %d:00", settings.digest_hour)

    print("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
