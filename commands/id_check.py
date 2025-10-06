import discord
# BHC-AMCC Google Sheet
APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbykFwV14QTs23UJxFvdJzb1GC3qbxz062omQNghqNk6xfKPhkaslKTp7DhjY_Q7uEdhNw/exec'
SECRET_TOKEN = 'lolibachtang'
# Đường dẫn log
LOG_FOLDER = "C:/Users/nguye/Downloads/DC_Bot_Geleven/Geleven_Logs"
BOOST_LOG_PATH = "C:/Users/nguye/Downloads/DC_Bot_Geleven/Geleven_Logs_Nitro/boosters_log.xlsx"
LOG_FILE_PATH = "C:/Users/nguye/Downloads/DC_Bot_Geleven/Geleven_Logs/add_bhg_logs.xlsx"
# ID Server
BHG_ID_Server = 1351910690499072072
AM_ID_Server = 733363418681049159
# Danh sách ID
ADMIN_IDS = [
    494485304192008202,  # Ati
    351361710130724868   # Thinh
]

MOD_IDS = [
    351361710130724868,  # Thinh
    764319600899915809,  # Akumayami
    333585660264972290,  # Thien
    972475113494679573,  # Micheal
    205194234460897299,  # Valentine
    594812248065835008,  # Phat
    1001450748590174279, # Savasel
    839380850793119744  # Daski
    #758974640378347540   # Phuc Fuca
]
# HÀM KIỂM TRA MỚI CHỈ DÙNG CHO LỆNH /RELOAD
def is_ati_admin(interaction: discord.Interaction) -> bool:
    """Kiểm tra: Phải là Admin (trong ADMIN_IDS) VÀ phải ở Server AM."""
    is_admin_user = int(interaction.user.id) in ADMIN_IDS
    is_on_am_server = interaction.guild_id == AM_ID_Server
    is_you = interaction.user.id == 494485304192008202
    
    return is_you and is_on_am_server # Hoặc chỉ dùng is_admin_user and is_on_am_server
    
def is_admin(interaction: discord.Interaction) -> bool:
    # Kiểm tra cả ID người dùng và ID máy chủ
    return int(interaction.user.id) in ADMIN_IDS and interaction.guild_id == BHG_ID_Server

def is_mod(interaction: discord.Interaction) -> bool:
    # Kiểm tra cả ID người dùng (hoặc admin) và ID máy chủ
    return (int(interaction.user.id) in MOD_IDS or int(interaction.user.id) in ADMIN_IDS) and interaction.guild_id == BHG_ID_Server

def is_allowed(interaction: discord.Interaction) -> bool:
    # Hàm này sẽ tự động kiểm tra cả ID người dùng và ID máy chủ
    return is_admin(interaction) or is_mod(interaction)