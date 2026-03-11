"""Telegram bot for Impact News onboarding and interaction."""

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

from user.onboarding import QUESTIONS, TIER2_SECTORS, EXCLUSIVE_OPTIONS, normalize_answer
from user.inference import connect_user_to_graph, enrich_user_graph
from graph.graph import ImpactGraph
from models import UserGraph
from config import settings

logger = logging.getLogger(__name__)

TOTAL_T1 = len(QUESTIONS)  # 10

# Conversation states for Tier 1 (0..9)
T1_STATES = range(TOTAL_T1)

# Tier 2 states: sector selection + per-sector question flow
T2_SELECT, T2_ANSWER = range(100, 102)

# Load graph at module level
graph = ImpactGraph(settings.graph_path)
graph.load()

USER_GRAPH_PATH = Path("data/user_graph.json")


def _save_user_graph(user_graph: UserGraph) -> None:
    """Persist user graph to disk."""
    Path("data").mkdir(exist_ok=True)
    with open(USER_GRAPH_PATH, "w") as f:
        json.dump(user_graph.model_dump(mode="json"), f, indent=2, default=list)


def _load_user_graph() -> UserGraph | None:
    """Load user graph from disk if it exists."""
    if USER_GRAPH_PATH.exists():
        with open(USER_GRAPH_PATH) as f:
            return UserGraph.model_validate(json.load(f))
    return None


# ---------------------------------------------------------------------------
# Tier 1: Core onboarding (10 questions)
# ---------------------------------------------------------------------------


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
    """Send Tier 1 question q_index to the user."""
    question = QUESTIONS[q_index]
    filled = "\u25cf" * (q_index + 1)
    remaining = "\u25cb" * (TOTAL_T1 - q_index - 1)
    text = f"Question {q_index + 1}/{TOTAL_T1}  {filled}{remaining}\n\n{question.text}"
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
    return 0  # first T1 state


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle all inline keyboard callbacks during Tier 1 onboarding."""
    query = update.callback_query
    await query.answer()

    data = query.data
    prefix, value = data.split(":", 1)

    # Find current question index by prefix
    q_index = next(i for i, q in enumerate(QUESTIONS) if q.callback_prefix == prefix)
    question = QUESTIONS[q_index]

    if question.multi_select:
        if value == "DONE":
            selections = context.user_data.get("multi_selections", [])
            answer_values = [normalize_answer(s) for s in selections]
            context.user_data["answers"][question.key] = answer_values
            context.user_data["multi_selections"] = []
        else:
            selections = context.user_data.get("multi_selections", [])

            if value in EXCLUSIVE_OPTIONS:
                if value in selections:
                    selections.remove(value)
                else:
                    selections = [value]
            else:
                selections = [s for s in selections if s not in EXCLUSIVE_OPTIONS]
                if value in selections:
                    selections.remove(value)
                else:
                    selections.append(value)

            context.user_data["multi_selections"] = selections
            keyboard = build_keyboard(question, selected=selections)
            filled = "\u25cf" * (q_index + 1)
            remaining = "\u25cb" * (TOTAL_T1 - q_index - 1)
            text = f"Question {q_index + 1}/{TOTAL_T1}  {filled}{remaining}\n\n{question.text}"
            await query.edit_message_text(text, reply_markup=keyboard)
            return q_index
    else:
        context.user_data["answers"][question.key] = normalize_answer(value)

    next_index = q_index + 1
    if next_index < TOTAL_T1:
        await send_question(update, context, next_index)
        return next_index
    else:
        return await finish_onboarding(update, context)


async def finish_onboarding(update, context) -> int:
    """Compute user graph from Tier 1, save, show summary."""
    answers = context.user_data["answers"]
    user_id = str(update.effective_user.id)

    user_graph = connect_user_to_graph(answers, graph, user_id=user_id)
    _save_user_graph(user_graph)

    summary = (
        f"Profile complete!\n\n"
        f"Direct connections: {len(user_graph.edges)} nodes\n"
        f"Reachable impact zone: {len(user_graph.reachable_nodes)} nodes\n\n"
        f"I'll track news that affects these areas of your life.\n"
        f"Use /profile to update anytime.\n"
        f"Use /explore to deep-dive into specific areas (investments, health, education, civic, consumer)."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(summary)
    else:
        await update.message.reply_text(summary)

    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Tier 2: Sector deep-dives via /explore
# ---------------------------------------------------------------------------


async def explore_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /explore — show available sectors."""
    user_graph = _load_user_graph()
    if user_graph is None:
        await update.message.reply_text(
            "You need to complete your profile first. Use /start to begin."
        )
        return ConversationHandler.END

    context.user_data["explore_user_graph"] = user_graph

    buttons = []
    for key, sector in TIER2_SECTORS.items():
        done = key in user_graph.completed_tiers
        label = f"\u2705 {sector['name']}" if done else sector["name"]
        buttons.append([InlineKeyboardButton(label, callback_data=f"sector:{key}")])
    buttons.append([InlineKeyboardButton("Cancel", callback_data="sector:cancel")])

    await update.message.reply_text(
        "Pick a sector to deep-dive into:\n"
        "(Completed sectors are marked with \u2705)",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return T2_SELECT


async def explore_select_sector(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle sector selection in /explore."""
    query = update.callback_query
    await query.answer()

    _, sector_key = query.data.split(":", 1)
    if sector_key == "cancel":
        await query.edit_message_text("Explore cancelled.")
        return ConversationHandler.END

    if sector_key not in TIER2_SECTORS:
        await query.edit_message_text("Unknown sector. Use /explore to try again.")
        return ConversationHandler.END

    sector = TIER2_SECTORS[sector_key]
    context.user_data["explore_sector"] = sector_key
    context.user_data["explore_questions"] = sector["questions"]
    context.user_data["explore_q_index"] = 0
    context.user_data["explore_answers"] = {}
    context.user_data["multi_selections"] = []

    await _send_explore_question(query, context, 0)
    return T2_ANSWER


async def _send_explore_question(query_or_update, context, q_index):
    """Send a Tier 2 question."""
    questions = context.user_data["explore_questions"]
    question = questions[q_index]
    total = len(questions)

    sector_name = TIER2_SECTORS[context.user_data["explore_sector"]]["name"]
    filled = "\u25cf" * (q_index + 1)
    remaining = "\u25cb" * (total - q_index - 1)
    text = f"{sector_name} {q_index + 1}/{total}  {filled}{remaining}\n\n{question.text}"

    keyboard = build_keyboard(question)
    if hasattr(query_or_update, "edit_message_text"):
        await query_or_update.edit_message_text(text, reply_markup=keyboard)
    elif hasattr(query_or_update, "callback_query") and query_or_update.callback_query:
        await query_or_update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await query_or_update.message.reply_text(text, reply_markup=keyboard)


async def explore_handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Tier 2 question answers."""
    query = update.callback_query
    await query.answer()

    data = query.data
    prefix, value = data.split(":", 1)

    questions = context.user_data["explore_questions"]
    q_index = next(i for i, q in enumerate(questions) if q.callback_prefix == prefix)
    question = questions[q_index]

    if question.multi_select:
        if value == "DONE":
            selections = context.user_data.get("multi_selections", [])
            answer_values = [normalize_answer(s) for s in selections]
            context.user_data["explore_answers"][question.key] = answer_values
            context.user_data["multi_selections"] = []
        else:
            selections = context.user_data.get("multi_selections", [])

            if value in EXCLUSIVE_OPTIONS:
                if value in selections:
                    selections.remove(value)
                else:
                    selections = [value]
            else:
                selections = [s for s in selections if s not in EXCLUSIVE_OPTIONS]
                if value in selections:
                    selections.remove(value)
                else:
                    selections.append(value)

            context.user_data["multi_selections"] = selections
            keyboard = build_keyboard(question, selected=selections)
            total = len(questions)
            sector_name = TIER2_SECTORS[context.user_data["explore_sector"]]["name"]
            filled = "\u25cf" * (q_index + 1)
            remaining = "\u25cb" * (total - q_index - 1)
            text = f"{sector_name} {q_index + 1}/{total}  {filled}{remaining}\n\n{question.text}"
            await query.edit_message_text(text, reply_markup=keyboard)
            return T2_ANSWER
    else:
        context.user_data["explore_answers"][question.key] = normalize_answer(value)

    next_index = q_index + 1
    if next_index < len(questions):
        await _send_explore_question(query, context, next_index)
        return T2_ANSWER
    else:
        return await finish_explore(update, context)


async def finish_explore(update, context) -> int:
    """Enrich user graph with Tier 2 answers."""
    sector_key = context.user_data["explore_sector"]
    answers = context.user_data["explore_answers"]
    user_graph = context.user_data["explore_user_graph"]

    enriched = enrich_user_graph(user_graph, sector_key, answers, graph)
    _save_user_graph(enriched)

    sector_name = TIER2_SECTORS[sector_key]["name"]
    summary = (
        f"{sector_name} deep-dive complete!\n\n"
        f"Direct connections: {len(enriched.edges)} nodes\n"
        f"Reachable impact zone: {len(enriched.reachable_nodes)} nodes\n"
        f"Completed: {', '.join(enriched.completed_tiers)}\n\n"
        f"Use /explore to dive into another sector."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(summary)
    else:
        await update.message.reply_text(summary)

    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    """Start the bot."""
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Tier 1 onboarding conversation
    t1_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("profile", start),
        ],
        states={i: [CallbackQueryHandler(handle_answer)] for i in range(TOTAL_T1)},
        fallbacks=[CommandHandler("start", start)],
    )

    # Tier 2 explore conversation
    t2_handler = ConversationHandler(
        entry_points=[CommandHandler("explore", explore_start)],
        states={
            T2_SELECT: [CallbackQueryHandler(explore_select_sector, pattern=r"^sector:")],
            T2_ANSWER: [CallbackQueryHandler(explore_handle_answer)],
        },
        fallbacks=[CommandHandler("explore", explore_start)],
    )

    app.add_handler(t1_handler)
    app.add_handler(t2_handler)

    print("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
