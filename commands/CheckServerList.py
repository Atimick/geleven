import discord
from discord import app_commands, Interaction, SelectOption
from discord.ext import commands
from discord.ui import Select, View
from commands.id_check import is_admin
from datetime import datetime, timedelta, timezone

# --- HELPER FUNCTION ---
def get_server_embed(guild: discord.Guild) -> discord.Embed:
    """Tạo Embed thông tin chi tiết cho một Server cụ thể."""
    vn_tz = timezone(timedelta(hours=7))
    
    # Cố gắng lấy Owner
    try:
        owner = guild.owner if guild.owner else guild.get_member(guild.owner_id)
        owner_info = f"👤 {owner.mention} (`{owner.id}`)" if owner else f"👤 Owner ID: `{guild.owner_id}`"
    except Exception:
        owner_info = f"👤 Owner ID: `{guild.owner_id}`"

    embed = discord.Embed(
        title=f"🌐 Thông Tin Server: {guild.name}",
        description=f"Server ID: `{guild.id}`",
        color=discord.Color.gold(),
        timestamp=datetime.now(vn_tz)
    )
    
    # Lấy thời gian tạo server và format lại
    created_at_vn = guild.created_at.astimezone(vn_tz)
    
    embed.add_field(name="Chủ Sở Hữu (Owner)", value=owner_info, inline=False)
    embed.add_field(name="Tổng Thành Viên", value=f"👥 {guild.member_count:,}", inline=True)
    embed.add_field(name="Kênh", value=f"💬 {len(guild.channels)}", inline=True)
    embed.add_field(name="Vai Trò (Roles)", value=f"👑 {len(guild.roles)}", inline=True)
    embed.add_field(name="Ngày Tạo Server", value=f"🗓️ {created_at_vn.strftime('%d/%m/%Y %H:%M:%S')} (VN)", inline=False)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.set_footer(text=f"Bot: {guild.me.display_name}", icon_url=guild.me.avatar.url if guild.me.avatar else None)
    
    return embed

# --- VIEW CÓ SELECT MENU ---
class ServerListView(View):
    def __init__(self, bot: commands.Bot, guilds: list[discord.Guild]):
        super().__init__(timeout=180) # Hết hạn sau 3 phút không tương tác
        self.bot = bot
        self.guilds_dict = {str(g.id): g for g in guilds}
        
        # Lấy tối đa 25 server để tạo options
        select_options = [
            SelectOption(label=g.name, value=str(g.id))
            for g in guilds[:25] # Chỉ lấy 25 server đầu tiên
        ]
        
        # Thêm Select Menu
        self.add_item(self.ServerSelect(select_options, self.guilds_dict))
        
        # Gửi Embed ban đầu khi View được tạo
        self.initial_embed = self.get_initial_embed(len(guilds))

    def get_initial_embed(self, total_count: int) -> discord.Embed:
        """Tạo Embed ban đầu khi chưa chọn server nào."""
        vn_tz = timezone(timedelta(hours=7))
        embed = discord.Embed(
            title=f"🌐 Danh Sách {total_count} Server Bot Đã Tham Gia",
            description="Vui lòng **chọn một Server** từ Menu bên dưới để xem thông tin chi tiết. (Chỉ hiển thị tối đa 25 server đầu tiên trong Menu)",
            color=discord.Color.blue(),
            timestamp=datetime.now(vn_tz)
        )
        embed.set_footer(text=f"Bot: {self.bot.user.name}", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        return embed

    # --- SELECT MENU CLASS ---
    class ServerSelect(Select):
        def __init__(self, options: list[SelectOption], guilds_dict: dict):
            super().__init__(
                placeholder="Chọn một Server...",
                options=options,
                custom_id="server_select_menu"
            )
            self.guilds_dict = guilds_dict

        async def callback(self, interaction: Interaction):
            # Lấy Guild ID từ giá trị Select Menu
            guild_id = interaction.data['values'][0]
            guild = self.guilds_dict.get(guild_id)

            if guild:
                # Tạo Embed mới cho server được chọn
                new_embed = get_server_embed(guild)
                
                # Chỉnh sửa tin nhắn gốc để hiển thị Embed mới
                await interaction.response.edit_message(embed=new_embed, view=self.view)
            else:
                await interaction.response.send_message("❌ Lỗi: Không tìm thấy Server này.", ephemeral=True)
                
    async def on_timeout(self):
        """Xử lý khi View hết hạn."""
        # Gỡ menu ra khỏi tin nhắn để không thể tương tác nữa
        try:
            message = self.message
            if message:
                await message.edit(content="Phiên Menu đã hết hạn.", view=None)
        except Exception:
            pass # Bỏ qua nếu tin nhắn đã bị xóa
            
# --- COG CLASS ---
class ServerList(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="am_server_list", description="[Admin] Hiển thị Menu danh sách server mà Bot đang ở (Chỉ Admin).")
    @app_commands.default_permissions(manage_guild=True)
    async def am_server_list_command(self, interaction: Interaction):
        
        # 1. KIỂM TRA QUYỀN HẠN
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Bạn không có quyền **Admin cứng** để sử dụng lệnh này.", ephemeral=True)
            return

        # 2. Bắt đầu xử lý (defer)
        await interaction.response.defer(thinking=True, ephemeral=True)

        # 3. Lấy danh sách Guilds
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True) # Sắp xếp theo số thành viên
        total_guilds = len(guilds)
        
        if total_guilds == 0:
            await interaction.followup.send("Bot hiện không tham gia server nào.", ephemeral=True)
            return

        # 4. Tạo View và Embed ban đầu
        view = ServerListView(self.bot, guilds)
        initial_embed = view.initial_embed

        # 5. Gửi tin nhắn với Menu List
        message = await interaction.followup.send(embed=initial_embed, view=view, ephemeral=True)
        view.message = message # Lưu lại tin nhắn để có thể chỉnh sửa khi hết hạn

# Định nghĩa hàm setup để Bot có thể load module này
async def setup(bot: commands.Bot):
    await bot.add_cog(ServerList(bot))