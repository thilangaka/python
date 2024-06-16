import logging
import os
import sqlite3
from fuzzywuzzy import process
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, PicklePersistence

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Define conversation states
ASKING_NAME, ASKING_QUESTION, CHANGING_NAME = range(3)

def get_response_from_db(query):
    """Fetch the closest matching response from the database."""
    db_path = 'D:/python/bot/bot_responses.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Fetch all questions to use for fuzzy matching
    c.execute("SELECT question FROM responses")
    questions = [row[0] for row in c.fetchall()]

    # Find the closest matching question
    closest_match = process.extractOne(query, questions)
    if closest_match and closest_match[1] >= 80:  # Adjust threshold as needed
        c.execute("SELECT response, image_url FROM responses WHERE question = ?", (closest_match[0],))
        response_row = c.fetchone()
        conn.close()
        return response_row
    conn.close()
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for the user's name."""
    logger.info(f"User {update.effective_user.id} started the bot.")
    await update.message.reply_text('Hi! What is your name?')
    return ASKING_NAME

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    logger.info(f"User {update.effective_user.id} asked for help.")
    await update.message.reply_text('Help!')

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for their name."""
    user_name = update.message.text
    context.user_data['name'] = user_name
    logger.info(f"User {update.effective_user.id} provided their name: {user_name}")
    await update.message.reply_text(f'Nice to meet you, {user_name}! Ask me anything.')
    return ASKING_QUESTION

async def change_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt the user to change their name."""
    await update.message.reply_text('What is your new name?')
    return CHANGING_NAME

async def update_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Update the user's name."""
    user_name = update.message.text
    context.user_data['name'] = user_name
    logger.info(f"User {update.effective_user.id} updated their name to: {user_name}")
    await update.message.reply_text(f'Got it, I will call you {user_name} from now on! Ask me anything.')
    return ASKING_QUESTION

async def respond_to_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Respond to predefined questions including images."""
    user_message = update.message.text.lower()
    user_name = context.user_data.get('name', 'there')
    logger.info(f"User {update.effective_user.id} sent a message: {user_message}")

    response_row = get_response_from_db(user_message)
    if response_row:
        response, image_path = response_row
        if image_path:
            if image_path.startswith('http'):
                # If the image path is a URL
                await update.message.reply_photo(photo=image_path, caption=f"{response} \nHope my answer is reasonable, {user_name}.")
            else:
                # If the image path is a local file path
                if os.path.exists(image_path):
                    with open(image_path, 'rb') as image_file:
                        await update.message.reply_photo(photo=image_file, caption=f"{response} {user_name}.")
                else:
                    logger.error(f"Image not found at path: {image_path}")
                    await update.message.reply_text(f"Sorry, {user_name}, I couldn't find the image.")
        else:
            await update.message.reply_text(f"{response} {user_name}.")
    else:
        await update.message.reply_text(f"I don't understand that question, {user_name}.")

def main() -> None:
    """Start the bot with persistence."""
    # Create the Application and pass it your bot's token.
    persistence = PicklePersistence(filepath='bot_data.pickle')
    application = Application.builder().token("7371737239:AAGtxlnv40RgaIso_ff5db47okPEgGUGg3M").persistence(persistence).build()

    # Define the conversation handler with the states ASKING_NAME, ASKING_QUESTION, and CHANGING_NAME
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASKING_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, respond_to_question),
                CommandHandler('changename', change_name)
            ],
            CHANGING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_name)]
        },
        fallbacks=[CommandHandler('help', help_command)],
        name="my_conversation",
        persistent=True,
    )

    # Add the conversation handler to the application
    application.add_handler(conv_handler)

    # Add the help command handler
    application.add_handler(CommandHandler('help', help_command))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
