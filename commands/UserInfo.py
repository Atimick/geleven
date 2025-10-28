import discord
from discord import app_commands, Interaction, SelectOption, Member
from discord.ext import commands
from discord.ui import Select, View
from datetime import datetime, timedelta, timezone

# --- HELPER FUNCTION: TẠO EMBED CHÍNH ---
def create_main_embed(member: Member) -> discord.Embed:
    """Tạo embed chính với thông tin cơ bản của user."""
    vn_tz = timezone(timedelta(hours=7))
    color = member.accent_color if member.accent_color else discord.Color.blue()

    # 1. TIÊU ĐỀ
    # Title: Tên hiển thị trong Server (Nickname > Username)
    # Description: Username gốc và ID
    embed = discord.Embed(
        title=f"User Infomations: {member.display_name}", 
        description=f"**Username:** @{member.name} (`{member.id}`)",
        color=color,
        timestamp=datetime.now(vn_tz)
    )

    # 2. THÔNG TIN CƠ BẢN
    
    nickname_status = member.nick if member.nick else "— None —"
    embed.add_field(name="Nickname Server", value=f"✏️ {nickname_status}", inline=False)
    
    created_at_vn = member.created_at.astimezone(vn_tz)
    embed.add_field(name="Account Create Time", value=f"🗓️ {created_at_vn.strftime('%d/%m/%Y %H:%M:%S')} (VN)", inline=True)

    joined_at_vn = member.joined_at.astimezone(vn_tz) if member.joined_at else "— Unknown —"
    embed.add_field(name="Account Join Server Time", value=f"👋 {joined_at_vn.strftime('%d/%m/%Y %H:%M:%S')} (VN)", inline=True)
    
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    if roles:
        role_list = ' '.join(roles) 
        
        embed.add_field(name=f"Roles ({len(roles)})", value=role_list, inline=False)
    
    embed.set_thumbnail(url=member.display_avatar.url)
    
    return embed

# --- HELPER FUNCTION: TẠO EMBED CHI TIẾT ---
def create_detail_embed(member: Member, detail_type: str) -> discord.Embed:
    """Avatars, Banners, Colors, Nitro."""
    
    # Màu profile
    color = member.accent_color if member.accent_color else discord.Color.blue()
    
    embed = discord.Embed(
        title=f"Thông Tin Chi Tiết: {member.display_name}",
        color=color
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    if detail_type == "nitro_info":
        
        # Trạng thái Nitro Booster (Server)
        nitro_status = "✅ Nitro Booster (Server)" if member.premium_since else "❌ Non-Nitro Booster"
        embed.add_field(name="Server Boost",
                        value=nitro_status, 
                        inline=False)
        
        if member.premium_since:
            vn_tz = timezone(timedelta(hours=7))
            boost_since_vn = member.premium_since.astimezone(vn_tz)
            embed.add_field(name="Boost Từ", 
                            value=f"✨ {boost_since_vn.strftime('%d/%m/%Y %H:%M:%S')} (VN)", 
                            inline=True)
        
    elif detail_type == "avatars_banners_colors":
        
        # 1. MÀU PROFILE
        color_hex = f"#{color.value:06X}" if member.accent_color else "— Màu mặc định"
        embed.add_field(name="Code Color", value=f"`{color_hex}`", inline=False)
        
        # 2. AVATAR (Ảnh đại diện)
        embed.add_field(name="— AVATARS —", value="\u200b", inline=False)
        
        # Avatar Gốc (User)
        user_avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        embed.add_field(name="Original Avatar User", value=f"[Check Picture]({user_avatar_url})", inline=True)
        
        # Avatar Server (display_avatar)
        server_avatar_url = member.display_avatar.url
        if member.display_avatar != member.avatar:
            embed.add_field(name="Avatar Server", value=f"✅ Changed ([Check Picture]({server_avatar_url}))", inline=True)
        else:
            embed.add_field(name="Avatar Server", value="— None -", inline=True)
    return embed

# --- VIEW CÓ SELECT MENU ---
class UserInfoView(View):
    def __init__(self, member: Member):
        super().__init__(timeout=180) 
        self.member = member
        self.add_item(self.DetailSelect(member))

    class DetailSelect(Select):
        def __init__(self, member: Member):
            options = [
                SelectOption(label="Classic Infomations", value="main", description="Show classic informations."),
                SelectOption(label="Theme Color, Avatars & Banners", value="avatars_banners_colors", description="Show Theme, Avatars, Banners of user."),
                SelectOption(label="Nitro Status", value="nitro_info", description="Status of Nitro and Boost Time."),
            ]
            super().__init__(
                placeholder="Select detail information type...",
                options=options,
                custom_id="userinfo_detail_menu"
            )
            self.member = member

        async def callback(self, interaction: Interaction):
            detail_type = interaction.data['values'][0]
            
            if detail_type == "main":
                new_embed = create_main_embed(self.member)
            else:
                new_embed = create_detail_embed(self.member, detail_type)
            
            # CHỈNH SỬA TIN NHẮN GỐC
            await interaction.response.edit_message(embed=new_embed, view=self.view)
                
# --- COG CLASS ---
class UserInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="userinfo", description="Check about a user.")
    @app_commands.describe(user="Choose a user to view information.")
    async def userinfo_command(self, interaction: Interaction, user: Member):
        
        await interaction.response.defer(thinking=True, ephemeral=False) 
        
        # 1. Tạo Embed chính
        main_embed = create_main_embed(user)
        
        # 2. Tạo View (bao gồm Select Menu)
        view = UserInfoView(user)
        
        # 3. Gửi tin nhắn với Embed chính và Menu
        message = await interaction.followup.send(embed=main_embed, view=view)
        view.message = message 

# Định nghĩa hàm setup
async def setup(bot: commands.Bot):
    await bot.add_cog(UserInfo(bot))