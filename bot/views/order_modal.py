import random
import asyncio
import aiohttp
import discord
from discord.ui import Modal, TextInput
from services import woolix
from bot.views.order_views import OrderConfirmView
from database.db import get_balance


class OrderModal(Modal):
    def __init__(self, fulfillment: str = "delivery"):
        super().__init__(title=f"Place {fulfillment.title()} Order")
        self.fulfillment = fulfillment
        self.cart_url = TextInput(
            label="DoorDash Group Cart Link",
            placeholder="https://drd.sh/...",
            required=True
        )
        self.address = TextInput(
            label="Delivery Address",
            placeholder="123 Main St, New York, NY 10001",
            required=True
        )
        self.order_name = TextInput(
            label="Order Name (Optional)",
            placeholder="Leave blank for default",
            required=False
        )
        self.add_item(self.cart_url)
        self.add_item(self.address)
        if self.fulfillment == "delivery":
            self.tip = TextInput(
                label="Dasher Tip ($)",
                default="2.00",
                required=False
            )
            self.add_item(self.tip)
        else:
            self.tip = None
        self.note = TextInput(
            label="Special Instructions",
            placeholder="Leave at door / Don't ring bell",
            required=False
        )
        self.add_item(self.note)
        self.add_item(self.order_name)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        random_unit = f"Apt {random.randint(1, 100)}"
        tip_cents = 0
        
        if self.fulfillment == "delivery" and self.tip and self.tip.value:
            try:
                tip_cents = int(float(self.tip.value.strip()) * 100)
            except ValueError:
                tip_cents = 200
                
        try:
            async with aiohttp.ClientSession() as session:
                data, status = await woolix.create_draft_job(
                    session,
                    group_cart=self.cart_url.value.strip(),
                    address=self.address.value.strip(),
                    fulfillment=self.fulfillment,
                    unit=random_unit,
                    tip_cents=tip_cents,
                    note=self.note.value.strip() if self.note.value else None,
                    name=self.order_name.value.strip() if self.order_name.value else None
                )
                
                if status not in [200, 201, 202]:
                    error_msg = (
                        data.get("error")
                        or data.get("message")
                        or str(data)
                    )
                    await interaction.followup.send(
                        f"❌ Error creating draft: `{error_msg}`",
                        ephemeral=True
                    )
                    return
                    
                job_id = data.get("job_id")
                await interaction.followup.send(
                    "⏳ Pricing cart and applying promotions...",
                    ephemeral=True
                )
                
                for _ in range(40):
                    await asyncio.sleep(3)
                    job_state, _ = await woolix.get_job(
                        session,
                        job_id
                    )
                    current_status = job_state.get("status")
                    
                    if current_status == "draft_ready":
                        # Fetch the user's current balance from the database
                        user_balance_cents = await get_balance(str(interaction.user.id))
                        user_balance_usd = user_balance_cents / 100

                        cart = job_state.get("cart", {})
                        base_total_cents = cart.get("client_total_cents", 0)
                        
                        # Add $1.00 (100 cents) service/processing upcharge
                        total_cents = base_total_cents + 100
                        final_total = total_cents / 100

                        subtotal = cart.get("subtotal_cents", 0) / 100
                        discount = cart.get("promo_discount_cents", 0) / 100
                        tax_and_fees = cart.get("tax_and_fees_cents", 0) / 100
                        tip_amount = (
                            tip_cents / 100
                            if self.fulfillment == "delivery"
                            else 0.00
                        )
                        items = cart.get("items", [])
                        item_lines = []
                        
                        for it in items:
                            name = it.get("name", "Item")
                            unit_price = it.get("unit_price_cents", 0) / 100
                            qty = it.get("quantity", 1)
                            item_lines.append(
                                f"• **{name}** (x{qty}) `${unit_price:.2f}`"
                            )
                            
                        items_overview = (
                            "\n".join(item_lines)
                            if item_lines
                            else "• *Cart items loaded*"
                        )
                        
                        embed = discord.Embed(
                            title=(
                                f"🛒 {cart.get('store_name', 'DoorDash')} "
                                f"({self.fulfillment.title()})"
                            ),
                            color=discord.Color.blue()
                        )
                        embed.add_field(
                            name="📍 Delivery Address",
                            value=f"{self.address.value} ({random_unit})",
                            inline=False
                        )
                        embed.add_field(
                            name="📋 Items Ordered",
                            value=items_overview,
                            inline=False
                        )
                        embed.add_field(
                            name="Subtotal",
                            value=f"${subtotal:.2f}",
                            inline=True
                        )
                        embed.add_field(
                            name="Promo Discount",
                            value=f"-${discount:.2f}",
                            inline=True
                        )
                        embed.add_field(
                            name="Taxes & Fees",
                            value=f"${tax_and_fees:.2f}",
                            inline=True
                        )
                        if self.fulfillment == "delivery":
                            embed.add_field(
                                name="Dasher Tip",
                                value=f"${tip_amount:.2f}",
                                inline=True
                            )
                        embed.add_field(
                            name="Service Fee",
                            value="$1.00",
                            inline=True
                        )
                        embed.add_field(
                            name="Total Due",
                            value=f"**${final_total:.2f}**",
                            inline=True
                        )
                        embed.add_field(
                            name="Your Balance",
                            value=f"${user_balance_usd:.2f}",
                            inline=True
                        )
                        embed.set_footer(
                            text="Draft held for 10 minutes."
                        )
                        
                        # total_cents (base + 100) is passed into OrderConfirmView
                        view = OrderConfirmView(
                            job_id,
                            total_cents,
                            interaction.user.id
                        )
                        await interaction.followup.send(
                            embed=embed,
                            view=view,
                            ephemeral=True
                        )
                        return
                        
                    elif current_status in [
                        "failed",
                        "cancelled",
                        "expired"
                    ]:
                        err = (
                            job_state
                            .get("error", {})
                            .get("message", "Job setup failed.")
                        )
                        await interaction.followup.send(
                            f"❌ Failed to build draft: `{err}`",
                            ephemeral=True
                        )
                        return
                        
                await interaction.followup.send(
                    "❌ Timed out waiting for draft to build.",
                    ephemeral=True
                )
                
        except Exception as e:
            print(f"[Order Modal Error]: {e}")
            await interaction.followup.send(
                f"❌ An error occurred: `{str(e)}`",
                ephemeral=True
            )