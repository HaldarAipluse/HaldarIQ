import os
import telebot
import google.generativeai as genai
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION ---
# PASTE YOUR NEW, SECRET KEYS IN THE QUOTATION MARKS BELOW
TELEGRAM_BOT_TOKEN = "8006163294:AAFtqfOMOmgpRd1yCURZNDJ8-r9tgydrXNg"
GEMINI_API_KEY = "AIzaSyCddPYpOxsqy0Z1pgE4WzgK6vttg3WLuF8"

# --- In-Memory Storage ---
user_generated_content = {}

# Check if keys are placeholders
if "YOUR_NEW" in TELEGRAM_BOT_TOKEN or "YOUR_NEW" in GEMINI_API_KEY:
    raise ValueError("ERROR: Please replace the placeholder text with your actual API keys in bot.py")

# --- GEMINI MODEL CONFIGURATION ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    raise RuntimeError(f"FATAL: Gemini API configuration failed. Check your key. Error: {e}")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# --- PROMPT ENGINEERING (FOR JSON OUTPUT) ---
# CHANGED BOT NAME HERE
JSON_PROMPT_TEMPLATE = """
Act as a world-class YouTube content strategist named 'HaldarIQ'.
Based on the user's video idea for a "{video_type}", generate a complete and diverse content strategy package.

Your response MUST be a valid JSON array containing exactly 5 unique JSON objects. Do not include any text or markdown before or after the JSON array.

Each JSON object in the array must have the following keys:
- "title": A catchy, SEO-friendly title. For a "YouTube Short", make it very short and punchy.
- "description": A detailed, SEO-optimized description. For a "YouTube Short", this can be 2-3 sentences.
- "hook_ideas": An array of 2 short, engaging sentences to use as hooks in the first 3 seconds of the video.
- "thumbnail_idea": A concise, creative idea for the video thumbnail.
- "tags": A comma-separated string of 15-20 relevant keywords and long-tail keywords.
- "hashtags": A comma-separated string of 3-4 strategic hashtags. For a "YouTube Short", ensure one of them is '#shorts'.

User's Idea: "{user_idea}"
"""

# --- BOT HANDLERS ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Sends the initial welcome message with video type choices."""
    markup = InlineKeyboardMarkup(row_width=2)
    long_video_btn = InlineKeyboardButton("🎬 YouTube Long Video", callback_data="long_video")
    shorts_video_btn = InlineKeyboardButton("⚡ YouTube Shorts Video", callback_data="shorts_video")
    markup.add(long_video_btn, shorts_video_btn)
    
    # CHANGED BOT NAME HERE
    welcome_text = "👋 Hello! I'm **HaldarIQ**.\n\nI'll craft a complete YouTube SEO plan for your video idea. What kind of video are you planning?"
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data in ["long_video", "shorts_video"])
def handle_video_type_selection(call):
    """Handles the user's choice of video type and asks for their idea."""
    video_type_text = "Long Video" if call.data == "long_video" else "YouTube Short"
    
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        f"✅ Great! You chose **{video_type_text}**.\n\nNow, please send me your video idea.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    
    bot.register_next_step_handler(call.message, get_video_idea, video_type_text)

def get_video_idea(message, video_type):
    """Receives the user's idea, calls the API, and presents title choices."""
    user_idea = message.text
    chat_id = message.chat.id
    
    thinking_message = bot.send_message(chat_id, "💠 *Analyzing your idea with HaldarIQ... Please wait.*", parse_mode='Markdown')

    try:
        prompt = JSON_PROMPT_TEMPLATE.format(video_type=video_type, user_idea=user_idea)
        response = model.generate_content(prompt)
        clean_json_str = response.text.strip().replace("```json", "").replace("```", "")
        content_plans = json.loads(clean_json_str)
        user_generated_content[chat_id] = content_plans
        
        markup = create_title_buttons(chat_id)
            
        bot.edit_message_text(
            "✨ **Analysis Complete!**\n\nI've generated 5 unique content plans. Choose a title below to see the full SEO strategy:",
            chat_id,
            thinking_message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        print(f"!!! An error occurred: {e}")
        bot.edit_message_text(
            "😥 **Oops! Something went wrong.**\n\nThis could be due to a safety block on the topic or an API error. Please try starting over with /start.",
            chat_id,
            thinking_message.message_id,
            parse_mode='Markdown'
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_details_"))
def show_full_details(call):
    """Displays the full, formatted details for the selected title and a back button."""
    chat_id = call.message.chat.id
    
    if chat_id not in user_generated_content:
        bot.answer_callback_query(call.id, "Sorry, this data has expired. Please /start over.", show_alert=True)
        return
        
    index = int(call.data.split('_')[2])
    plan = user_generated_content[chat_id][index]
    
    details_text = (
        f"✅ **Plan for: {plan['title']}**\n\n"
        f"📝 **SEO Description:**\n{plan['description']}\n\n"
        f"💡 **Hook Ideas (First 3 Seconds):**\n"
        f" - \"{plan['hook_ideas'][0]}\"\n"
        f" - \"{plan['hook_ideas'][1]}\"\n\n"
        f"🖼️ **Thumbnail Idea:**\n{plan['thumbnail_idea']}\n\n"
        f"🏷️ **Keywords/Tags:**\n`{plan['tags']}`\n\n"
        f"#️⃣ **Hashtags:**\n`{plan['hashtags'].replace(',', ' ')}`"
    )
    
    markup = InlineKeyboardMarkup()
    back_button = InlineKeyboardButton("⬅️ Back to Titles", callback_data="back_to_titles")
    markup.add(back_button)
    
    bot.edit_message_text(details_text, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_titles")
def handle_back_to_titles(call):
    """Edits the message to show the title selection screen again."""
    chat_id = call.message.chat.id
    
    if chat_id not in user_generated_content:
        bot.answer_callback_query(call.id, "Sorry, this data has expired. Please /start over.", show_alert=True)
        return
        
    markup = create_title_buttons(chat_id)
    
    bot.edit_message_text(
        "✨ **Analysis Complete!**\n\nI've generated 5 unique content plans. Choose a title below to see the full SEO strategy:",
        chat_id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

def create_title_buttons(chat_id):
    """Creates an InlineKeyboardMarkup with buttons for each generated title."""
    markup = InlineKeyboardMarkup(row_width=1)
    if chat_id in user_generated_content:
        for i, plan in enumerate(user_generated_content[chat_id]):
            button = InlineKeyboardButton(plan['title'], callback_data=f"show_details_{i}")
            markup.add(button)
    return markup


# --- START THE BOT ---
if __name__ == '__main__':
    print("Modern YouTube SEO Bot (HaldarIQ) is running...")
    bot.infinity_polling(timeout=60)
