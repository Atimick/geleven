import discord
import asyncio
from discord import FFmpegPCMAudio
import time

class MusicQueue:
    def __init__(self):
        self.queue = []
        self.vc = None
        self.is_playing = False
        self.bot = None # BẮT BUỘC: Lưu trữ bot instance để truy cập loop an toàn
        self.current_song = None
        self.start_time = None
    def add_song(self, song_data):
        self.queue.append(song_data)

    def get_next_song(self):
        return self.queue.pop(0) if self.queue else None

    def has_next(self):
        return len(self.queue) > 0

    async def stop(self):
        """Dừng phát và xoá hàng đợi"""
        self.queue.clear()
        self.current_song = None
        self.start_time = None
        self.is_playing = False
        if self.vc and self.vc.is_connected():
            # Đảm bảo dừng voice client trước khi disconnect
            if self.vc.is_playing() or self.vc.is_paused():
                self.vc.stop() 
            await self.vc.disconnect()
            self.vc = None

    async def play_next(self, channel: discord.TextChannel): # SỬA: Thay interaction bằng channel
        if not self.queue or not self.vc:
            self.is_playing = False
            self.current_song = None
            self.start_time = None
            return

        song = self.get_next_song()
        self.is_playing = True
        self.current_song = song
        self.start_time = time.time()

        try:
            # Source file từ URL
            source = FFmpegPCMAudio(song['url'], before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5')
            
            # Đảm bảo dừng bài cũ nếu có
            if self.vc.is_playing() or self.vc.is_paused():
                self.vc.stop()

            # SỬA QUAN TRỌNG: Sử dụng bot.loop để đặt tác vụ cho after_song
            if self.bot is None:
                raise Exception("Bot instance chưa được gán cho MusicQueue.")

            after_func = lambda e: self.bot.loop.call_soon_threadsafe(
                asyncio.create_task, 
                self._after_song(channel) # Truyền channel
            )
            
            self.vc.play(source, after=after_func)
            
            # Gửi thông báo
            embed = discord.Embed(
                title="▶️ Đang phát",
                description=f"[{song['title']}]({song['webpage_url']})",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Yêu cầu bởi: {song['requester'].display_name}")
            await channel.send(embed=embed) # Gửi vào channel

        except Exception as e:
            print(f"[LỖI PHÁT BÀI] {e}")
            await channel.send(f"❌ Không thể phát bài tiếp theo: {e}") # SỬA: Gửi vào channel
            self.is_playing = False
            self.current_song = None
            self.start_time = None
            if self.vc and self.vc.is_connected():
                await self.vc.disconnect()
                self.vc = None

    async def _after_song(self, channel: discord.TextChannel): # SỬA: Thay interaction bằng channel
        await asyncio.sleep(1)
        if self.has_next():
            await self.play_next(channel) # SỬA: Truyền channel
        else:
            self.is_playing = False
            self.current_song = None
            self.start_time = None
            
            # Khởi động tính năng tự động ngắt kết nối
            await self._auto_disconnect_after_timeout(channel)

    async def _auto_disconnect_after_timeout(self, channel: discord.TextChannel, timeout: int = 300):
        await asyncio.sleep(timeout)
        # Kiểm tra lại: nếu bot vẫn không phát và vẫn đang kết nối
        if not self.is_playing and self.vc and self.vc.is_connected():
            await self.vc.disconnect()
            self.vc = None
            try:
                await channel.send("👋 Bot đã rời voice channel do không còn bài để phát.")
            except:
                pass