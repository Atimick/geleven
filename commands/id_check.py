import discord
from discord import Interaction

DB_PATH = "sqlite:///bot_data.db"
# BHC-AMCC Google Sheet
APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbykFwV14QTs23UJxFvdJzb1GC3qbxz062omQNgho9k6xfKPhkaslKTp7DhjY_Q7uEdhNw/exec'
TICKET_SHEET_URL = 'https://script.google.com/macros/s/AKfycby_ZEUmXn4JCI8vsuFJ37Mwvj-0CnPHI2aVZnPd057e5N6v8yJA_Y9nD7UxqCbrhm-OiQ/exec'
SECRET_TOKEN = 'lolibachtang'

# Đường dẫn log
#LOG_FOLDER = "C:/Users/nguye/Downloads/DC_Bot_Geleven/Geleven_Logs"
BOOST_LOG_PATH = "C:/Users/nguye/Downloads/DC_Bot_Geleven/Geleven_Logs_Nitro/boosters_log.xlsx"
#LOG_FILE_PATH = "C:/Users/nguye/Downloads/DC_Bot_Geleven/Geleven_Logs/add_bhg_logs.xlsx"

# ID Server
BHG_ID_Server = 1351910690499072072
AM_ID_Server = 733363418681049159

# Danh sách ID Admin cứng (được phép dùng lệnh trên mọi server)
ADMIN_IDS = [
    494485304192008202,  # Ati
    351361710130724868,  # Thinh
    594812248065835008   # Phat
]

# Danh sách ID quản lý lệnh BHG (Có thể thay đổi thủ công độc lập)
BHG_MANAGER_IDS = [
    494485304192008202,  # Ati
    972475113494679573,  # Michael
    333585660264972290   # Thien
]

# --- HÀM KIỂM TRA QUYỀN HẠN ---
def is_bhg_manager(interaction: discord.Interaction) -> bool:
    """Kiểm tra: ID người dùng phải có trong BHG_MANAGER_IDS (ID quản lý thủ công)."""
    return int(interaction.user.id) in BHG_MANAGER_IDS

def is_ati_admin(interaction: Interaction) -> bool:
    """Kiểm tra: Phải là Ati VÀ phải ở Server AM. (Giữ nguyên)"""
    is_admin_user = int(interaction.user.id) in ADMIN_IDS
    is_on_am_server = interaction.guild_id == AM_ID_Server
    is_you = interaction.user.id == 494485304192008202
    
    return is_you and is_on_am_server

def is_admin(interaction: Interaction) -> bool:
    """
    Cấp độ 1 (Cao nhất): ID người dùng phải có trong ADMIN_IDS. 
    Chỉ dùng cho các lệnh đặc biệt.
    """
    return int(interaction.user.id) in ADMIN_IDS

def is_allowed(interaction: Interaction) -> bool:
    """
    Cấp độ 2 (Thông thường):
    1. Là Admin cứng (trong ADMIN_IDS). HOẶC
    2. Có quyền 'Manage Server' trong Server hiện tại.
    """
    # 1. Kiểm tra Admin cứng
    if is_admin(interaction):
        return True

    # 2. Kiểm tra quyền 'Manage Server'
    if interaction.guild is None:
        return False
    
    member = interaction.user
    
    # Kiểm tra quyền 'manage_guild' (Manage Server)
    return member.guild_permissions.manage_guild