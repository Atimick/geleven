import discord
from discord.ext import commands
from discord import app_commands
import random
import re
import textwrap
import secrets
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .id_check import DB_PATH 

# --- CẤU HÌNH LOGGING SQLALCHEMY ---
Engine = create_engine(DB_PATH) 
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=Engine) 

class RollCommandLog(Base):
    """Mô hình SQLAlchemy cho bảng logs việc sử dụng lệnh Roll."""
    __tablename__ = 'roll_command_logs' # Tên bảng mới
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    guild_id = Column(String) 
    guild_name = Column(String) 
    channel_id = Column(String)
    command_name = Column(String) 
    dice_formula = Column(String) 
    roll_result = Column(Integer) 
    user_id = Column(String)
    user_name = Column(String)

# TẠO BẢNG MỚI roll_command_logs trong bot_data.db nếu chưa có
Base.metadata.create_all(Engine) 

class PubRoll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Slash command ---
    @app_commands.command(name="roll", description="Roll a dice (Ex: 1d20, 2d6+3, 1d1000-5)")
    async def roll_slash(self, interaction: discord.Interaction, dice: str):
        await self._handle_roll(dice, interaction.user, interaction=interaction)

    # --- Prefix command ---
    @commands.command(name="r")
    async def roll_prefix(self, ctx, *, dice: str):
        await self._handle_roll(dice, ctx.author, ctx=ctx)

    # --- Xử lý chung ---
    async def _handle_roll(self, dice: str, user, interaction: discord.Interaction = None, ctx: commands.Context = None):
        original_dice = dice
        is_simple_dice_roll = False
        try:
            dice = dice.strip().lower()
            parts = re.split(r'(\+|-)', dice)

            total = 0
            details = []
            operator = '+'
            
            rolls = []
            sides = 0
            num = 1

            for part in parts:
                part = part.strip()
                if not part:
                    continue

                if part in ['+', '-']:
                    operator = part
                else:
                    match = re.match(r'(\d*)d(\d+)', part)
                    if match:
                        num = int(match.group(1)) if match.group(1) else 1
                        sides = int(match.group(2))
                        if num <= 0 or sides <= 0:
                            raise ValueError("Số lượng hoặc mặt của xúc xắc không hợp lệ.")

                        current_rolls = [secrets.randbelow(sides) + 1 for _ in range(num)]
                        rolls.extend(current_rolls)
                        
                        subtotal = sum(current_rolls)
                        if operator == '-':
                            subtotal = -subtotal
                        total += subtotal
                        details.append(f"{'-' if operator == '-' else ''}{num}d{sides} ({', '.join(map(str, current_rolls))})")
                    else:
                        try:
                            number = int(part)
                            if operator == '-':
                                number = -number
                            total += number
                            details.append(f"{operator} {abs(number)}")
                        except ValueError:
                            raise ValueError(f"Không hiểu cú pháp: {part}")

            if not details:
                raise ValueError("Không có cú pháp hợp lệ.")
            
            embed = discord.Embed(
                color=discord.Color.dark_purple()
            )
            
            embed.set_author(
                name="Dice Roller", 
                icon_url="https://i.imgur.com/n6t1V2I.png"
            )
            
            embed.set_footer(text=f"Người roll: {user.display_name}")
            
            if len(parts) == 1 and re.match(r'(\d*)d(\d+)', parts[0].strip()):
                roll_result_str = ", ".join(map(str, rolls)) if rolls else " "
                roll_sum_str = str(total)
                average = total / num if num > 0 else 0
                avg_str = f"{average:.2f}"
                
                ROLLS_COL_WIDTH = 16
                SUM_COL_WIDTH = 8
                AVG_COL_WIDTH = 8
                TOTAL_INNER_WIDTH = ROLLS_COL_WIDTH + SUM_COL_WIDTH + AVG_COL_WIDTH + 2
                
                if len(roll_result_str) <= ROLLS_COL_WIDTH - 2:
                    is_simple_dice_roll = True
                    
                    dice_title_content = original_dice.upper().center(TOTAL_INNER_WIDTH)
                    rolls_title = "rolls".center(ROLLS_COL_WIDTH)
                    sum_title = "sum".center(SUM_COL_WIDTH)
                    avg_title = "avg".center(AVG_COL_WIDTH)
                    roll_content = roll_result_str.center(ROLLS_COL_WIDTH)
                    sum_content_bracketed = f"[{roll_sum_str}]".center(SUM_COL_WIDTH)
                    avg_content_bracketed = f"[{avg_str}]".center(AVG_COL_WIDTH)
                    
                    LINE_FULL = "═" * TOTAL_INNER_WIDTH
                    LINE_ROLLS = "═" * ROLLS_COL_WIDTH
                    LINE_SUM = "═" * SUM_COL_WIDTH
                    LINE_AVG = "═" * AVG_COL_WIDTH
                    
                    table_content = textwrap.dedent(f"""
                        ╔{LINE_FULL}╗
                        ║{dice_title_content}║
                        ╠{LINE_ROLLS}╦{LINE_SUM}╦{LINE_AVG}╣
                        ║{rolls_title}║{sum_title}║{avg_title}║
                        ╠{LINE_ROLLS}╬{LINE_SUM}╬{LINE_AVG}╣
                        ║{roll_content}║{sum_content_bracketed}║{avg_content_bracketed}║
                        ╚{LINE_ROLLS}╩{LINE_SUM}╩{LINE_AVG}╝
                    """)
                    
                    embed.description = f"```\n{table_content}\n```"
                
                else:
                    roll_lines = textwrap.wrap(roll_result_str, width=ROLLS_COL_WIDTH - 2)
                    max_lines = len(roll_lines)
                    
                    if max_lines > 10:
                        is_simple_dice_roll = False
                    else:
                        is_simple_dice_roll = True
                        
                        dice_title_content = original_dice.upper().center(TOTAL_INNER_WIDTH)
                        rolls_title = "rolls".center(ROLLS_COL_WIDTH)
                        sum_title = "sum".center(SUM_COL_WIDTH)
                        avg_title = "avg".center(AVG_COL_WIDTH)
                        
                        LINE_FULL = "═" * TOTAL_INNER_WIDTH
                        LINE_ROLLS = "═" * ROLLS_COL_WIDTH
                        LINE_SUM = "═" * SUM_COL_WIDTH
                        LINE_AVG = "═" * AVG_COL_WIDTH
                        
                        # Build content lines
                        content_lines = []
                        sum_content_bracketed = f"[{roll_sum_str}]".center(SUM_COL_WIDTH)
                        avg_content_bracketed = f"[{avg_str}]".center(AVG_COL_WIDTH)
                        for i in range(max_lines):
                            roll_line = roll_lines[i].center(ROLLS_COL_WIDTH)
                            if i == max_lines - 1:
                                sum_line = sum_content_bracketed
                                avg_line = avg_content_bracketed
                            else:
                                sum_line = " " * SUM_COL_WIDTH
                                avg_line = " " * AVG_COL_WIDTH
                            content_lines.append(f"║{roll_line}║{sum_line}║{avg_line}║")
                        
                        table_content = textwrap.dedent(f"""
                            ╔{LINE_FULL}╗
                            ║{dice_title_content}║
                            ╠{LINE_ROLLS}╦{LINE_SUM}╦{LINE_AVG}╣
                            ║{rolls_title}║{sum_title}║{avg_title}║
                            ╠{LINE_ROLLS}╬{LINE_SUM}╬{LINE_AVG}╣
                        """) + "\n".join(content_lines) + f"\n╚{LINE_ROLLS}╩{LINE_SUM}╩{LINE_AVG}╝"
                        
                        embed.description = f"```\n{table_content}\n```"

            if not is_simple_dice_roll:
                result_str = f"**Kết quả:** {total}\n\n**Chi tiết:**\n" + "\n".join(details)
                embed_description = textwrap.shorten(result_str, width=2000, placeholder="...")
                embed.description = embed_description
                embed.add_field(name="Lệnh gốc", value=original_dice, inline=False)

            if interaction:
                await interaction.response.send_message(embed=embed)
                self.log_command_usage(user, "roll", original_dice, total, interaction)
            elif ctx:
                await ctx.send(embed=embed)
                self.log_command_usage(user, "r", original_dice, total, ctx)

        except Exception as e:
            error_msg = f"❌ Lỗi: {str(e)}"
            if interaction:
                if not interaction.response.is_done():
                    await interaction.response.send_message(error_msg, ephemeral=True)
                else:
                    await interaction.followup.send(error_msg, ephemeral=True)
            elif ctx:
                await ctx.send(error_msg)

    def log_command_usage(self, user: discord.User, command_name: str, dice_formula: str, roll_result: int, source):
        session = Session() 
        try:
            guild = source.guild
            channel_id = str(source.channel.id) if source.channel else "DM"
            
            guild_id = str(guild.id) if guild else "DM"
            guild_name = guild.name if guild else "DM"
            
            new_log = RollCommandLog(
                guild_id=guild_id,
                guild_name=guild_name,
                channel_id=channel_id,
                command_name=command_name,
                dice_formula=dice_formula,
                roll_result=roll_result,
                user_id=str(user.id),
                user_name=str(user)
            )
            
            session.add(new_log)
            session.commit()
            
        except Exception as db_error:
            session.rollback() 
            print(f"Lỗi khi ghi logs SQLAlchemy cho /roll: {db_error}") 
        finally:
            session.close()

async def setup(bot: commands.Bot):
    await bot.add_cog(PubRoll(bot))