"""Telegram bot for Impact News onboarding and interaction."""

import json
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
from config import settings

# Conversation states
(CITY, WORK_SECTOR, HOUSING, COMMUTE, LOANS, INVESTMENTS, DIET, DEPENDENTS, HEALTH) = range(9)

# Load graph at module level
graph = ImpactGraph(settings.graph_path)
graph.load()


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


def main():
    """Start the bot."""
    app = Application.builder().token(settings.telegram_bot_token).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("profile", start),
        ],
        states={i: [CallbackQueryHandler(handle_answer)] for i in range(9)},
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    print("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
