import discord
import zipfile
import aiofiles
import os
from discord import app_commands
from discord.ext import commands
import random, datetime, asyncio, aiohttp, io
from zoneinfo import ZoneInfo
from commands.id_check import SECRET_TOKEN, TICKET_SHEET_URL 

class TicketSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # 🔧 Config: Ánh xạ Guild ID với Category và Log Channel tương ứng
        # Sử dụng TÊN ROLE để tự tìm Role Staff trong Guild
        self.GUILD_CONFIGS = {
            733363418681049159: { #AM
                "CATEGORY_ID": 1430370909725790339,
                "LOG_CHANNEL_ID": 1430372059531313294,
                # 🛑 CẦN THIẾT: Điền TÊN chính xác của role Staff/Mod (Ví dụ: "Admin", "Modder", "Quản Trị Viên")
                "STAFF_ROLE_NAME": "TÊN_ROLE_STAFF_AM", # <--- HÃY ĐIỀN TÊN ROLE ĐÚNG TẠI ĐÂY
            },
            1351910690499072072: { #BHG
                "CATEGORY_ID": 1430438851410923602,
                "LOG_CHANNEL_ID": 1352122809538838531,
                "STAFF_ROLE_NAME": "Modder",
            },
            # Thêm các server khác...
        }

    # ---------------------------
    # 🎫 /ticket create
    # ---------------------------
    @app_commands.command(name="ticket_create", description="Tạo một ticket mới")
    @app_commands.describe(noidung="Lý do hoặc mô tả yêu cầu của bạn")
    async def ticket_create(self, interaction: discord.Interaction, noidung: str):
        guild = interaction.guild
        user = interaction.user
        
        # Lấy config cho Guild hiện tại
        guild_config = self.GUILD_CONFIGS.get(guild.id)
        if not guild_config:
            await interaction.response.send_message("❌ Server này chưa được cấu hình cho hệ thống ticket.", ephemeral=True)
            return
                
        # Lấy STAFF_ROLE_NAME và Category ID
        category_id = guild_config["CATEGORY_ID"]
        staff_role_name = guild_config["STAFF_ROLE_NAME"] # Lấy tên role
        
        # Kiểm tra user đã có ticket chưa (cần kiểm tra cả Category ID)
        for ch in guild.text_channels:
            # Kiểm tra: kênh phải là ticket-XXX VÀ người dùng là thành viên VÀ nằm trong category chính xác
            if ch.name.startswith("ticket-") and user in ch.members and ch.category_id == category_id:
                await interaction.response.send_message(
                    f"⚠️ Bạn đã có một ticket đang mở: {ch.mention}",
                    ephemeral=True
                )
                return

        # Sinh tên ticket: ticket-YYMMDD-1234
        date = datetime.datetime.now().strftime("%y%m%d")
        rand = random.randint(1000, 9999)
        ticket_name = f"ticket-{date}-{rand}"

        category = guild.get_channel(category_id)
        if not category:
            await interaction.response.send_message("❌ Không tìm thấy Category Ticket.", ephemeral=True)
            return
        
        # === 1. TÌM ROLE STAFF THEO TÊN (Không phụ thuộc vào ID) ===
        staff_role = discord.utils.get(guild.roles, name=staff_role_name)
        
        if not staff_role:
             # Cảnh báo nếu không tìm thấy role theo tên (Dù vẫn tạo ticket, nhưng staff không thấy)
             print(f"⚠️ Cảnh báo: Không tìm thấy Role Staff có tên '{staff_role_name}' trong Guild {guild.name}. Staff sẽ không thấy ticket mới.")
        # =================================

        # 2. Thiết lập quyền cơ bản
        overwrites = {
            # Bắt buộc CẤM @everyone (để ẩn ticket)
            guild.default_role: discord.PermissionOverwrite(read_messages=False), 
            # Bắt buộc CHO PHÉP người tạo ticket
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # 3. Ghi đè quyền cho Role Staff/Mod nếu tìm thấy
        # Đây là bước quan trọng để đảm bảo Staff thấy kênh, tránh lỗi kế thừa Discord
        if staff_role:
            # Ghi đè quyền cho Role Staff/Mod: CHO PHÉP đọc và gửi tin nhắn
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # 🔴 Thêm ID người tạo vào Topic của kênh để truy xuất chính xác
        # Format: TICKET_OPENER_ID:1234567890 | Lý do mở ticket: Mô tả
        topic_content = f"TICKET_OPENER_ID:{user.id} | Lý do mở ticket: {noidung}"
        
        channel = await category.create_text_channel(
            name=ticket_name, 
            overwrites=overwrites, 
            topic=topic_content
        )

        embed = discord.Embed(
            title="🎫 Ticket Được Tạo!",
            description=f"Người yêu cầu: {user.mention}\n**Lý do:** {noidung}",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Staff sẽ sớm hỗ trợ bạn.")
        await channel.send(embed=embed)
        await interaction.response.send_message(
            f"✅ Ticket của bạn đã được tạo: {channel.mention}", ephemeral=True
        )

    # ---------------------------
    # 🎫 /ticket close
    # ---------------------------
    @app_commands.command(name="ticket_close", description="Đóng ticket, lưu log và gửi đến Google Sheet")
    async def ticket_close(self, interaction: discord.Interaction):
        # Sử dụng is_mod() để kiểm tra người dùng có quyền đóng ticket không
        if not is_mod(interaction):
            await interaction.response.send_message(
                "🚫 Bạn không có quyền đóng ticket này.",
                ephemeral=True
            )
            return

        channel = interaction.channel
        if not channel.name.startswith("ticket-"):
            await interaction.response.send_message(
                "⚠️ Lệnh này chỉ dùng trong kênh ticket!",
                ephemeral=True
            )
            return

        await interaction.response.send_message("⏳ Saving...", ephemeral=True)

        # === Tra cứu cấu hình cho Guild hiện tại ===
        guild_config = self.GUILD_CONFIGS.get(interaction.guild_id)
        if not guild_config:
            await interaction.followup.send("❌ Server này chưa được cấu hình cho hệ thống ticket.", ephemeral=True)
            return
            
        LOG_CHANNEL_ID = guild_config["LOG_CHANNEL_ID"] 
        # ============================================

        # === Lấy người tạo ticket BẰNG CÁCH PARSE TOPIC ===
        ticket_opener = None
        opener_id = "Unknown"
        opener_name = "Unknown"
        
        # 1. Tìm ID từ Topic
        if channel.topic and "TICKET_OPENER_ID:" in channel.topic:
            try:
                # Phân tích Topic: Lấy phần đầu tiên (trước |)
                topic_parts = channel.topic.split('|', 1)
                id_part = topic_parts[0].strip()
                
                if id_part.startswith("TICKET_OPENER_ID:"):
                    opener_id = id_part.split(':')[1].strip()
                    ticket_opener = self.bot.get_user(int(opener_id))
                    
                    if ticket_opener:
                        opener_name = str(ticket_opener)
                    else:
                        opener_name = f"User Rời Server ({opener_id})"
                        
            except Exception as e:
                print(f"Lỗi khi parse ticket opener ID từ topic: {e}")
                
        # 2. Fallback cho ticket cũ hoặc lỗi parse
        if opener_id == "Unknown":
            async for msg in channel.history(limit=50, oldest_first=True):
                if not msg.author.bot:
                    ticket_opener = msg.author
                    opener_id = str(ticket_opener.id)
                    opener_name = str(ticket_opener)
                    break
            if opener_id == "Unknown":
                opener_name = "Unknown (Chỉ có Bot/Ticket cũ)"
        # =================================================================================
        vn_timezone = ZoneInfo("Asia/Ho_Chi_Minh")
        
        # Open Time (Thời gian mở ticket, lấy từ created_at của kênh)
        open_time_utc = channel.created_at
        open_time_vn = open_time_utc.astimezone(vn_timezone).strftime("%Y-%m-%d %H:%M:%S")

        # Closed Time (Thời gian đóng ticket, là thời điểm hiện tại)
        closed_time_utc_naive = datetime.datetime.now()
        closed_time_utc = closed_time_utc_naive.replace(tzinfo=datetime.timezone.utc)
        closed_time_vn = closed_time_utc.astimezone(vn_timezone).strftime("%Y-%m-%d %H:%M:%S")
        # =====================================
        
        # Thiết lập đường dẫn file tạm
        os.makedirs("temp_logs", exist_ok=True)
        transcript_name = f"{channel.name}_transcript.txt"
        transcript_path = os.path.join("temp_logs", transcript_name)
        zip_filename = f"{channel.name}_log.zip"
        zip_path = os.path.join("temp_logs", zip_filename)
        download_paths = [] # Danh sách các đường dẫn file đính kèm

        # ---- 1️⃣ Gửi lên Google Sheet ----
        ticket_info = channel.topic.split('|', 1)[1].strip() if channel.topic and '|' in channel.topic else channel.topic or "(Không có ghi chú)"
        
        payload = {
            "secret": SECRET_TOKEN,
            "server_id": str(interaction.guild.id),
            "ticket_id": channel.name,
            "category_id": str(channel.category_id or ""),
            "ticket_info": ticket_info,
            "user_id": opener_id, 
            "user_name": opener_name, 
            "open_time": open_time_vn, 
            "staff_id": str(interaction.user.id),
            "staff_name": str(interaction.user),
            "closed_time": closed_time_vn,
            "zip_log_url": f"https://discord.com/channels/{interaction.guild.id}/{LOG_CHANNEL_ID}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(TICKET_SHEET_URL, json=payload) as resp:
                sheet_ok = resp.status == 200

        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)

        if log_channel is None:
            print(f"⚠️ Không tìm thấy kênh hoặc thread có ID {LOG_CHANNEL_ID}")
            log_ok = False
        else:
            # Nếu thread bị archive thì mở lại để gửi được
            if isinstance(log_channel, discord.Thread) and log_channel.archived:
                try:
                    await log_channel.edit(archived=False, locked=False)
                except Exception as e:
                    print(f"⚠️ Không thể mở lại thread: {e}")

            # === 2️⃣ Thu thập nội dung tin nhắn và tải file đính kèm ===
            messages = []
            attachments = []

            async for msg in channel.history(limit=None, oldest_first=True):
                content = msg.content.replace("\n", " ")
                line = f"[{msg.created_at.astimezone(vn_timezone).strftime('%Y-%m-%d %H:%M:%S')}] {msg.author}: {content}"

                if msg.attachments:
                    urls = []
                    for att in msg.attachments:
                        urls.append(att.url)
                        attachments.append(att)
                        
                        # Tải file đính kèm
                        try:
                            file_path = os.path.join("temp_logs", f"{att.id}_{att.filename}")
                            await att.save(file_path)
                            download_paths.append(file_path)
                        except Exception as e:
                            print(f"⚠️ Không tải được file {att.filename}: {e}")

                    line += f" [📎 Attachments: {' '.join(urls)}]"

                messages.append(line)

            transcript_text = "\n".join(messages) or "(Không có tin nhắn)"

            # === 3️⃣ Lưu file transcript ===
            async with aiofiles.open(transcript_path, mode="w", encoding="utf-8") as f:
                await f.write(transcript_text)

            # === 4️⃣ TẠO file ZIP (Sử dụng asyncio.to_thread cho tác vụ chặn) ===
            def create_zip_blocking():
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    # Ghi transcript
                    zipf.write(transcript_path, os.path.basename(transcript_path))
                    # Ghi các file đính kèm đã tải
                    for f in download_paths:
                        zipf.write(f, os.path.basename(f))
            
            await asyncio.to_thread(create_zip_blocking)
            
            # === 5️⃣ Gửi log lên thread ===
            embed = discord.Embed(
                title="📦 Ticket Log (Full)",
                description=f"**Ticket:** {channel.name}\n**Closed by:** {interaction.user.mention}\n**Thời gian đóng (VN):** {closed_time_vn}\n**Tổng số file:** {len(download_paths)}",
                color=discord.Color.orange()
            )
            embed.add_field(name="Server gốc", value=f"{interaction.guild.name} (`{interaction.guild.id}`)", inline=False)
            embed.set_footer(text="Geleven Ticket Log")

            try:
                await log_channel.send(embed=embed, file=discord.File(zip_path))
                log_ok = True
            except Exception as e:
                log_ok = False
                print(f"⚠️ Lỗi gửi log: {e}")

            # === 6️⃣ Xoá file tạm (Sử dụng asyncio.to_thread) ===
            def cleanup_blocking():
                try:
                    os.remove(transcript_path)
                    os.remove(zip_path)
                    for f in download_paths:
                        os.remove(f)
                except Exception as e:
                    print(f"⚠️ Không thể xoá file tạm: {e}")

            await asyncio.to_thread(cleanup_blocking)
        
        # 7️⃣ Gửi phản hồi cuối cùng và Xoá kênh ticket
        # Gửi phản hồi followup TRƯỚC khi xóa kênh để tránh lỗi "Unknown Channel"
        try:
            # Gửi thông báo hoàn tất đến người dùng qua phản hồi tương tác (followup)
            await interaction.followup.send(
                f"✅ Ticket **{channel.name}** đã được đóng và xóa. Thời gian đóng: **{closed_time_vn}**",
                ephemeral=True
            )
            
            # Đợi một chút để đảm bảo Discord xử lý xong phản hồi webhook
            await asyncio.sleep(0.5) 
            
            # Tiến hành xóa kênh
            await channel.delete(reason="Ticket closed by staff command /ticket_close")
            
        except Exception as e:
            # Xử lý nếu kênh bị xóa quá nhanh hoặc các lỗi khác
            if "Unknown Channel" not in str(e):
                print(f"Lỗi khi xóa kênh hoặc gửi followup: {e}")
                # Nếu lỗi không phải do kênh bị xóa, ta cố gắng gửi thông báo lỗi xóa kênh
                await interaction.followup.send(
                    f"❌ Đã lưu log nhưng không thể xóa kênh. Lỗi: {e}",
                    ephemeral=True
                )
            else:
                 # Ghi nhận kênh bị xóa quá nhanh nhưng không gửi thêm followup (tránh lỗi lặp)
                 print(f"LỖI: Kênh đã bị xóa trước khi gửi phản hồi cuối cùng. Bỏ qua lỗi {e}")


# 🚀 Bắt buộc phải có hàm setup để Discord.py có thể load module này
async def setup(bot: commands.Bot):
    await bot.add_cog(TicketSystem(bot))
