import telebot
import io
import pandas as pd
import re

# BotFather থেকে পাওয়া API Token এখানে বসান
API_TOKEN = '8622758649:AAFJNmXbfJMgYzQR6SHCvIWIacaIIqBFzN8'

bot = telebot.TeleBot(API_TOKEN)

# ইউজারের পাঠানো ডাটা সাময়িকভাবে জমা রাখার জন্য ডিকশনারি
user_buffer = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "মেথড হান্টার অ্যাডভান্স বাফার বোট-এ স্বাগতম!\n\n"
        "নিয়মাবলী:\n"
        "১. কমা দিয়ে আলাদা করা ডাটা পাঠান (যেমন: ১২৩,৪৫৬,৭৮৯)।\n"
        "২. এক্সেল ফাইল (.xlsx) পাঠান, আমি 'Number' কলামটি খুঁজে বের করে সেটিকে টেক্সট ফাইল করে দেব।\n"
        "৩. কাজ শেষ হলে 'done' লিখে পাঠান।\n"
        "৪. আমি আপনাকে সব ডাটা সাজিয়ে একটি .txt ফাইল দেব।\n\n"
        "নতুন করে শুরু করতে চাইলে /clear লিখুন।"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['clear'])
def clear_data(message):
    user_id = message.from_user.id
    if user_id in user_buffer:
        user_buffer[user_id] = []
    bot.reply_to(message, "আপনার আগের সব ডাটা মুছে ফেলা হয়েছে। এখন নতুন ডাটা পাঠাতে পারেন।")

# এক্সেল ফাইল প্রসেস করার সিস্টেম
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    file_name = message.document.file_name
    
    if file_name.endswith(('.xlsx', '.xls')):
        bot.reply_to(message, "এক্সেল ফাইলটি প্রসেস করা হচ্ছে, একটু অপেক্ষা করুন...")
        
        try:
            # ফাইল ডাউনলোড করা
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # এক্সেল রিড করা
            df = pd.read_excel(io.BytesIO(downloaded_file), header=None)
            
            target_col_index = None
            header_row_index = None
            target_col_name = "Number"
            
            # প্রথম ২০টি রো চেক করে 'Number' কলামটি খোঁজা (আরও গভীরভাবে স্ক্যান করা হচ্ছে)
            for r_idx, row in df.head(20).iterrows():
                for c_idx, cell in enumerate(row):
                    if cell and isinstance(cell, str):
                        clean_cell = cell.strip().lower()
                        # শুধুমাত্র 'number' শব্দটা আছে কি না তা নিখুঁতভাবে চেক করা
                        if clean_cell == 'number' or clean_cell == 'numbers' or re.search(r'\bnumber\b', clean_cell):
                            target_col_index = c_idx
                            header_row_index = r_idx
                            target_col_name = cell.strip()
                            break
                if target_col_index is not None:
                    break
            
            if target_col_index is not None:
                # নম্বর ডেটা নেওয়া
                numbers_data = df.iloc[header_row_index + 1:, target_col_index]
                raw_numbers = numbers_data.dropna().tolist()
                
                processed_numbers = []
                for n in raw_numbers:
                    # যদি নম্বরটি ফ্লোট বা সায়েন্টিফিক নোটেশনে থাকে (যেমন ১২৩.০), সেটিকে ক্লিন করা
                    try:
                        if isinstance(n, (int, float)):
                            n_str = str(int(n))
                        else:
                            n_str = str(n).strip()
                            # যদি স্ট্রিং-এর শেষে .0 থাকে, সেটি বাদ দেওয়া
                            if n_str.endswith('.0'):
                                n_str = n_str[:-2]
                        
                        if n_str:
                            processed_numbers.append(n_str)
                    except:
                        continue

                if processed_numbers:
                    final_string = "\n".join(processed_numbers)
                    
                    # মেমরিতে টেক্সট ফাইল তৈরি করা
                    bio = io.BytesIO()
                    bio.name = f"extracted_{file_name.split('.')[0]}.txt"
                    bio.write(final_string.encode('utf-8'))
                    bio.seek(0)
                    
                    bot.send_document(message.chat.id, bio, caption=f"'{target_col_name}' কলাম থেকে মোট {len(processed_numbers)}টি নম্বর বের করা হয়েছে।")
                else:
                    bot.reply_to(message, "এরর: এই কলামে কোনো ভ্যালিড নম্বর খুঁজে পাওয়া যায়নি।")
            else:
                bot.reply_to(message, "এরর: এক্সেল ফাইলে 'Number' নামের কোনো কলাম বা হেডার খুঁজে পাওয়া যায়নি! দয়া করে কলামের নাম 'Number' কি না চেক করুন।")
                
        except Exception as e:
            bot.reply_to(message, f"ফাইলটি প্রসেস করতে সমস্যা হয়েছে: {str(e)}")
    else:
        bot.reply_to(message, "দয়া করে শুধুমাত্র .xlsx বা .xls ফাইল পাঠান।")

# সাধারণ টেক্সট মেসেজ হ্যান্ডলার
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if text.lower() == 'done':
        if user_id not in user_buffer or not user_buffer[user_id]:
            bot.reply_to(message, "আপনি এখনো কোনো ডাটা পাঠাননি!")
            return

        bot.send_chat_action(message.chat.id, 'upload_document')
        final_string = "\n".join(user_buffer[user_id])
        
        if final_string.strip():
            bio = io.BytesIO()
            bio.name = "method_hunter_data.txt"
            bio.write(final_string.encode('utf-8'))
            bio.seek(0)

            bot.send_document(message.chat.id, bio, caption=f"মোট আইটেম সংখ্যা: {len(user_buffer[user_id])}\nকাজ শেষ! ফাইলটি ডাউনলোড করে নিন।")
            user_buffer[user_id] = []
        else:
            bot.reply_to(message, "বাফার খালি।")

    else:
        if user_id not in user_buffer:
            user_buffer[user_id] = []
        
        new_items = [item.strip() for item in text.split(',') if item.strip()]
        user_buffer[user_id].extend(new_items)
        bot.reply_to(message, f"{len(new_items)}টি আইটেম যোগ করা হয়েছে। বর্তমানে মোট: {len(user_buffer[user_id])}। কাজ শেষ হলে 'done' লিখুন।")

if __name__ == "__main__":
    print("বোটটি সফলভাবে চালু হয়েছে...")
    bot.infinity_polling()
