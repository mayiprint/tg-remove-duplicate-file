import asyncio.subprocess
import logging
from tqdm import tqdm
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel, DocumentAttributeFilename, DocumentAttributeVideo, MessageMediaPhoto, PhotoSizeProgressive

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, filename='logfile.log')
logger = logging.getLogger(__name__)
queue = asyncio.Queue()

api_id = 1 # 請替換成自己api_id
api_hash = '' # 請替換成自己api_hash

# 群組列表
chat_list = ['https://t.me/*'] # 請替換成自己想要監聽群組

# 計算檔案大小
def convert_size(text):
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = 1024
    for i in range(len(units)):
        if (text/ size) < 1:
            return "%.2f%s" % (text, units[i])
        text = text/ size
    return 0

# 取得檔案資訊
def get_file_information(message):
    file = None
    if message.media is not None:
        try:
            if type(message.media) is MessageMediaPhoto:
                photo = message.media.photo
                file = { 
                    'id': photo.id,
                    'access_hash': photo.access_hash,
                    'type': 'photo',
                    'datetime': photo.date.astimezone().strftime("%Y/%m/%d %H:%M:%S")
                }
                for i in photo.sizes:
                    if type(i) is PhotoSizeProgressive: # 檔案名稱
                        file["size"] = i.sizes[len(i.sizes)-1] # 影片名稱
                        file["w"] = i.w  # 影片寬度
                        file["h"] = i.h  # 影片高度
            else:
                document = message.media.document
                file = { 
                    'id': document.id,
                    'access_hash': document.access_hash,
                    'type': document.mime_type, # 檔案類型
                    'size': document.size, # 檔案尺寸
                    'datetime': document.date.astimezone().strftime("%Y/%m/%d %H:%M:%S")
                }
                for i in document.attributes:
                    if type(i) is DocumentAttributeFilename: # 檔案名稱
                        file["name"] = i.file_name # 影片名稱
                    if type(i) is DocumentAttributeVideo: # 影片解析度
                        file["w"] = i.w  # 影片寬度
                        file["h"] = i.h  # 影片高度
        except:
            print("發生錯誤")
            print(message)
            return None
        
    return file

# 檢查是否有存在相同檔案id
def check_duplicate_file(message, entity):
    file = get_file_information(message)
    if file is None: return False, file
    if file['id'] in file_list[entity.id]:
        return True, file
    file_list[entity.id].append(file['id'])

    return False, file

file_list = {} # 紀錄檔案id

@events.register(events.NewMessage(chats=tuple(chat_list)))
async def handler(update):
    # 獲得群組新資訊
    chat_id = update.message.to_id
    try:
        entity = await client.get_entity(chat_id)
    except ValueError:
        entity = await client.get_entity(PeerChannel(chat_id))
    except Exception as e:
        logger.error(type(e.__class__, e))
        return

    text = ""
    print("群組:{}, 新訊息".format(entity.title))
    is_duplicate, file = check_duplicate_file(update.message, entity)
    if is_duplicate:
        text += "時間:{}".format(file['datetime'])
        if 'type' in  file: text += ", 檔案類型:{}".format(file['type'])
        if 'name' in file:text += ", 檔案名稱:{}".format(file['name'])
        text += ", 檔案大小:{}".format(convert_size(file['size']))
        if 'w' in file and 'h' in file:
            text += ", 解析度:{}x{}".format(file['w'],file['h'])
        print(text)
        await client.delete_messages(entity=entity, message_ids=[update.message.id]) # 刪除訊息
            

async def init():
    bar = tqdm(chat_list)
    for i in bar:
        entity = await client.get_entity(i)
        file_list[entity.id] = [] # 初始化每個群組檔案列表
        total = 0 # 統計處理訊息數量
        delete = 0 # 統計刪除訊息數量

        # 讀取群組訊息(由舊到新)
        async for message in client.iter_messages(entity, reverse = True):
            is_duplicate, _ = check_duplicate_file(message, entity)
            if is_duplicate:
                print('群組:{}, 重複檔案進行刪除[{}]'.format(entity.title,message.id))
                await client.delete_messages(entity=entity, message_ids=[message.id])  # 刪除訊息
                delete += 1
            total += 1
            bar.set_description('群組:{} 初始化檢查重複檔案, 檢查數量:{}, 刪除:{}'.format(entity.title, total, delete))
        
    return False

client = TelegramClient('bot', api_id, api_hash)
with client:
    print("初始化檢查重複檔案")
    client.loop.run_until_complete(init())

    print("開始監聽新訊息：")
    client.add_event_handler(handler)
    client.run_until_disconnected()