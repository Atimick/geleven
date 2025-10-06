# CommandsPublicMusic.py
import discord
import time
import yt_dlp
import asyncio
from discord.ext import commands
from discord import app_commands
from discord import FFmpegPCMAudio
from .CommandsPublicMusic_Queue import MusicQueue
from .CommandsPublicMusic_Control import MusicControlView # Import View

guild_queues = {}

def get_music_queue(guild_id, bot: commands.Bot) -> MusicQueue:
    """Lấy hoặc tạo MusicQueue cho Guild ID cụ thể."""
    if guild_id not in guild_queues:
        music_queue = MusicQueue()
        music_queue.bot = bot # Gán bot instance CHỈ KHI TẠO
        guild_queues[guild_id] = music_queue
    return guild_queues[guild_id]


async def setup(bot: commands.Bot):
    @bot.tree.command(name="play", description="Phát nhạc từ YouTube hoặc Playlist")
    @app_commands.describe(url="Link YouTube hoặc từ khóa")
    async def play(interaction: discord.Interaction, url: str):
        # Bước 1: Defer Interaction ngay lập tức
        await interaction.response.defer(thinking=True)
        
        # 1. KIỂM TRA GUILD VÀ USER
        if not interaction.guild:
            await interaction.followup.send("❌ Lệnh này chỉ hoạt động trong server.", ephemeral=True)
            return
            
        music_queue = get_music_queue(interaction.guild.id, bot)

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("❌ Bạn cần vào voice channel trước!", ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        
        # 2. KHAI BÁO BIẾN
        max_retries = 3
        retry_delay = 2

        # 3. VÒNG LẶP KẾT NỐI VOICE (CHỈ CÓ MỘT LẦN CHẠY DUY NHẤT)
        vc = interaction.guild.voice_client
        for attempt in range(max_retries):
            try:
                # Nếu bot chưa kết nối, kết nối mới
                if vc is None:
                    vc = await voice_channel.connect(timeout=10.0, reconnect=True)
                # Nếu bot đã kết nối nhưng ở kênh khác, di chuyển
                elif vc.channel != voice_channel:
                    await vc.move_to(voice_channel)
                # Nếu bot đã kết nối và ở đúng kênh, không làm gì
                
                music_queue.vc = vc
                break # Kết nối thành công, thoát vòng lặp
            
            except Exception as e:
                # Xử lý khi kết nối thất bại
                print(f"[LỖI KẾT NỐI VOICE] Thử {attempt+1}/{max_retries}: {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    # Logic SỬA LỖI 4006: Buộc ngắt kết nối dứt khoát nếu thất bại
                    if interaction.guild.voice_client:
                        try:
                            # Đảm bảo bot không bị kẹt trong trạng thái voice lỗi
                            await interaction.guild.voice_client.disconnect(force=True)
                        except:
                            pass 
                            
                    music_queue.vc = None
                    
                    await interaction.followup.send(
                        "❌ Không thể kết nối đến voice channel sau nhiều lần thử. Vui lòng thử lại sau 5 giây.", 
                        ephemeral=True
                    )
                    return # Thoát lệnh vì đã thất bại

        # 4. LOGIC XỬ LÝ NHẠC (Phần này đã ổn định)
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'default_search': 'auto',
            'noplaylist': False,
            'extract_flat': False,
            'force_generic_extractor': False,
            'socket_timeout': 10,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                entries = info['entries'] if 'entries' in info else [info]
                added_count = 0
                
                for entry in entries:
                    stream_url = None
                    # ... (logic lấy stream_url giữ nguyên)
                    try:
                        # Thử lấy URL từ formats
                        formats = entry.get('formats', [])
                        audio_format = next((f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none'), None)
                        stream_url = audio_format['url'] if audio_format else None
                    except Exception as e:
                        print(f"[LỖI LẤY URL] {e}")

                    if not stream_url:
                        print(f"[LỖI] Không tìm thấy stream URL cho: {entry.get('title')}")
                        continue
                    
                    song = {
                        'title': entry.get('title', 'Không rõ tiêu đề'),
                        'url': stream_url,
                        'webpage_url': entry.get('webpage_url', url),
                        'requester': interaction.user
                    }
                    music_queue.add_song(song)
                    added_count += 1
                if added_count == 0:
                    await interaction.followup.send("❌ Không tìm thấy bài hát hợp lệ để thêm vào hàng đợi.", ephemeral=True)
                    return

                embed = discord.Embed(
                    title="🎵 Đã thêm vào hàng đợi",
                    description=f"✅ Đã thêm `{added_count}` bài vào hàng đợi.",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
                
                # Bắt đầu phát nếu bot chưa phát
                if not music_queue.is_playing:
                    await music_queue.play_next(interaction.channel)

        except Exception as e:
            print(f"[LỖI PLAY] {e}")
            await interaction.followup.send("❌ Không thể phát video hoặc playlist. Lỗi: " + str(e), ephemeral=True)

    @bot.tree.command(name="stop", description="Dừng phát nhạc và rời khỏi voice channel")
    async def stop(interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Lệnh này chỉ hoạt động trong server.", ephemeral=True)
            return

        music_queue = get_music_queue(interaction.guild.id, bot)
        vc = interaction.guild.voice_client

        if vc and vc.is_connected():
            await music_queue.stop() # Dừng phát, xoá hàng đợi, ngắt kết nối an toàn
            await interaction.response.send_message("⛔ Bot đã rời voice channel.", ephemeral=True)
            # Xoá queue của Guild để dọn dẹp bộ nhớ
            if interaction.guild.id in guild_queues:
                del guild_queues[interaction.guild.id]
        else:
            await interaction.response.send_message("❌ Bot không ở voice channel nào.", ephemeral=True)

    @bot.tree.command(name="status", description="Kiểm tra trạng thái bot nhạc")
    async def status(interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Lệnh này chỉ hoạt động trong server.", ephemeral=True)
            return

        # Lấy queue của Guild
        music_queue = get_music_queue(interaction.guild.id, bot)
        
        # ... (Logic tạo Embed giữ nguyên, sử dụng music_queue đã lấy)

        embed = discord.Embed(title="🎵 Trạng thái bot nhạc", color=discord.Color.blue())
        if music_queue.is_playing and music_queue.current_song:
            elapsed_time = time.time() - music_queue.start_time if music_queue.start_time else 0
            minutes, seconds = divmod(int(elapsed_time), 60)
            elapsed_str = f"{minutes:02d}:{seconds:02d}"
            embed.add_field(
                name="Đang phát",
                value=f"[{music_queue.current_song['title']}]({music_queue.current_song['webpage_url']})\n"
                      f"👤 Yêu cầu bởi: {music_queue.current_song['requester'].mention}\n"
                      f"⏰ Thời gian: {elapsed_str}",
                inline=False
            )
        else:
            embed.add_field(name="Đang phát", value="Không có bài nào đang phát", inline=False)
        
        embed.add_field(name="Kết nối voice", value="Đã kết nối" if music_queue.vc and music_queue.vc.is_connected() else "Chưa kết nối", inline=False)
        embed.add_field(name="Hàng đợi", value=f"{len(music_queue.queue)} bài" if music_queue.queue else "Trống", inline=False)
        await interaction.response.send_message(embed=embed)