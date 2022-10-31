#!/usr/bin/env python
# coding: utf-8

# In[20]:


get_ipython().system('python -m pip install pyTelegramBotAPI six')


# In[22]:


get_ipython().system('pip install pymongo')


# In[1]:


import telebot
from telebot import types
import requests
from pymongo import MongoClient
import pandas as pd
from tqdm import tqdm


# In[2]:


start_text = ' سلام! به بات جمع آوری داده گفتار خوش آمدید.\n  این بات به منظور تهیه پیکره فارسی به انگلیسی برای پروژه های تشخیص گفتار و ترجمه گفتار در پژوهش های مربوط به هوش مصنوعی و پردازش زبان طبیعی مورد استفاده واقع می شود. پیشاپیش از حمایت شما ممنونیم.. \n آزمایشگاه پردازش زبان طبیعی دانشگاه تهران'

# commands = ['دریافت جمله', 'ارزیابی جمله']
# Goodbye_record = "صدای شما ضبط شد. \n از حمایت شما ممنونیم. \n\nاگر مایل به ارسال یک جمله دیگر هستید گزینه 'دریافت جمله' و اگر می خواهید گفتار یک جمله را ارزیابی کنید گزینه 'ارزیابی جمله' را انتخاب کنید. "
# Goodbye_validation = "ارزیابی شما ارسال شد. \n از حمایت شما ممنونیم. \n\nاگر مایل به ارزیابی یک جمله دیگر هستید گزینه 'ارزیابی جمله' و اگر می خواهید یک جمله جدید را ضبط کنید گزینه 'دریافت جمله' را انتخاب کنید. "
# help = "برای ضبط جمله گزینه 'دریافت جمله' و برای ارزیابی گفتارهای ضبط شده گزینه 'ارزیابی جمله' را انتخاب کنید."

covost_en_fa_all_url = "./tele/corpus/covost_v2.en_fa.tsv"


# In[3]:


df = pd.read_csv(covost_en_fa_all_url, sep='\t', header=0)
df.head()


# In[4]:


myclient = MongoClient("*****")
mydb = myclient["local"]
sent_col = mydb["sentence_table"]
valid_col = mydb["validation_table"]
myclient.list_database_names()


# In[29]:


# mylist = []
# for index, row in tqdm(df.iterrows()):
#     id = row['path'].split("en_")[1]
#     if len(id) < 2 :
#       continue
#     id = str(index) + "_" + id[1].split('.')[0]
#     sample = {
#       'txt':  row['translation'],
#       '_id' : id,
#       'choose_num' : 0
#     }
#     mylist.append(sample)

# x = sent_col.insert_many(mylist)


# In[5]:


def random_sample():
    a = sent_col.aggregate([{"$sample": {"size": 1}}, {"$match": {"choose_num": {"$lte": 5}}}])
    sample = list(a)[0]
#     choose_num = sample['choose_num']
    return sample

def update_choose_num(id, ch_n):
    myquery = {"_id": id}
    newvalues = {"$set": {"choose_num": ch_n+1}}
    sent_col.update_one(myquery, newvalues)

rs = random_sample()
print(rs)


# In[18]:


TOKEN = "****"
CHAT_ID = "@SpeechRTBot"

bot = telebot.TeleBot(TOKEN, parse_mode=None)
# last_id = []
# last_choose_num = []
user = bot.get_me()
chat_id = user.id
updates = bot.get_updates()
data_entries = []
map = {}


# In[ ]:


def record_command_handler(message):
  sample = random_sample()
  bot.send_message(message.from_user.id, sample['txt'])
  if message.from_user.id not in map.keys():
     map[message.from_user.id]= {"last_id":0, "last_choose_num":0}
  map[message.from_user.id]["last_id"] = sample['_id']
  map[message.from_user.id]["last_choose_num"] = sample['choose_num']
  existing_document = users_col.find_one(message.from_user.id)
  if not existing_document:
    user = {"_id": message.from_user.id, "username":message.from_user.username}
    col_record = users_col.insert_one(user)
  bot.send_message(message.from_user.id, sample['_id'], sample['choose_num'])

def record_handler(message):
  file_info = bot.get_file(message.voice.file_id)
  chat_id = message.from_user.id
  last_choose_num = map[message.from_user.id]["last_choose_num"]
  last_id = map[message.from_user.id]["last_id"]
  try: 
      file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(TOKEN, file_info.file_path))
      filepath = "/content/gdrive/MyDrive/telebot/{}_{}_{}.wav".format(str(last_id), str(last_choose_num), str(message.from_user.id))
      # print(filepath)
      with open(filepath, mode='bx') as f:
          f.write(file.content)
      f.close()
      # print("finish write")
      bot.send_message(message.from_user.id, str(last_id) + str(last_choose_num) + "✅")
      update_choose_num(last_id, last_choose_num)
      text = sent_col.find_one({"_id": last_id})['txt']
      col_record = valid_col.insert_one({"_id": "{}_{}".format(str(last_id), str(last_choose_num)), "txt": text, "filepath": filepath, "valid_cnt": 0, "validations": []})
      record_command_handler(message)
  except Exception as e:
      print(e)


# In[ ]:


class Entry:
  def __init__(self, text, audio_path, is_validated):
    self.text = text
    self.audio_path = audio_path
    self.is_validated = is_validated

@bot.message_handler(commands=['start'])
def new_sentence(message):
  bot.send_message(message.from_user.id, start_text)
  bot.send_message(message.from_user.id, "لطفا از روی جملات زیر بخوانید و صدای خود را ارسال کنید. ")
  keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
  # speak_button = types.KeyboardButton(text="جمله بعدی")
  # validate_button = types.KeyboardButton(text=commands[1])
  # keyboard.add(speak_button)
  record_command_handler(message)
  # keyboard.add(validate_button)
  # bot.send_message(message.chat.id, help, reply_markup=keyboard)


@bot.message_handler(content_types=['text'])
def handle_message(message):
  # if message.text == commands[0]:
  record_command_handler(message)
  # elif message.text == commands[1]:
    # validate_command_handler(message)
  # else:
    # validate_handler(message)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
  record_handler(message)

bot.polling()


# In[ ]:




