import asyncio
import aiohttp
import discord
from discord.ui import Button, View

from database.db import (
    adjust_balance,
    get_balance,
    log_order,
    queue_for_refund
)
from services import woolix
from services.notifier import send_order_success_webhook
from services.card_pool import pop_card

STAFF_CHANNEL_ID = 1542209360040562838

class OrderConfirmView(View):
    def __init__(
        self,
        job_id: str,
        cost_cents: int,
        user_id: int
    ):
        super().__init__(timeout=600)
        self.job_id = job_id
        self.cost_cents = cost_cents
        self.user_id = user_id
        self.clicked = False

    @discord.ui.button(
        label="Confirm & Place Order",
        style=discord.ButtonStyle.green
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This prompt is not yours.",
                ephemeral=True
            )
            return

        if self.clicked:
            await interaction.response.send_message(
                "  This order is already being processed.",
                ephemeral=True
            )
            return

        self.clicked = True
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            "  Placing order with DoorDash...",
            ephemeral=True
        )
        
        current_balance = await get_balance(
            str(self.user_id)
        )
        
        if current_balance < self.cost_cents:
            await interaction.followup.send(
                (
                    f"  Insufficient balance. "
                    f"You need **${self.cost_cents / 100:.2f}**, "
                    f"but have **${current_balance / 100:.2f}**."
                ),
                ephemeral=True
            )
            return
            
        # Card is only taken when Confirm is clicked
        card = pop_card()
        if not card:
            await interaction.followup.send(
                "  No payment cards are currently available.",
                ephemeral=True
            )
            return

        async with aiohttp.ClientSession() as session:
            # 1. Attach the card
            config_data, config_status = await woolix.configure_job(session, self.job_id, card=card)
            if config_status not in [200, 201]:
                await interaction.followup.send(
                    f"  Failed to attach card: {config_data.get('error', 'Unknown Error')}", 
                    ephemeral=True
                )
                return

            # 2. Place the order
            proceed_data, status = await woolix.proceed_job(
                session,
                self.job_id
            )

            # -------------------------------------------------
            # IMPORTANT FIX:
            #
            # Woolix verification can continue for ~3 minutes.
            # Do NOT call the order failed just because the
            # initial /proceed response isn't final yet.
            # -------------------------------------------------
            final_data = proceed_data

            # Give Woolix up to roughly 3 minutes
            # to settle the real payment outcome.
            for _ in range(36):
                payment_status = final_data.get("payment_status")
                tracking_url = final_data.get("tracking_url")
                job_status = final_data.get("status")
                
                # Tracking URL means the order really exists.
                if tracking_url:
                    break
                # Explicit success
                if payment_status == "succeeded":
                    break
                # Explicit final decline/failure
                if payment_status in ["declined", "failed"]:
                    break
                # Terminal job failure
                if job_status in ["failed", "cancelled", "expired"]:
                    break
                    
                await asyncio.sleep(5)
                
                try:
                    job_check, check_status = await woolix.get_job(
                        session,
                        self.job_id
                    )
                    if check_status == 200:
                        final_data = job_check
                except Exception as e:
                    print(
                        f"[ORDER VERIFY POLL ERROR] "
                        f"{self.job_id}: {e}"
                    )

            payment_status = final_data.get("payment_status")
            tracking_url = final_data.get("tracking_url")
            order_uuid = final_data.get("order_uuid")
            account_email = final_data.get("account_email")
            account_password = final_data.get("account_password")

            # ---------------------------------------------
            # SUCCESS
            #
            # tracking_url is the strongest signal here.
            # ---------------------------------------------
            order_succeeded = bool(
                tracking_url
                or payment_status == "succeeded"
            )

            if order_succeeded:
                await adjust_balance(
                    str(self.user_id),
                    -self.cost_cents
                )
                await log_order(
                    self.job_id,
                    str(self.user_id),
                    self.cost_cents,
                    "placed",
                    tracking_url
                )

                # Keep existing refund queue functionality
                if account_email and account_password:
                    await queue_for_refund(
                        self.job_id,
                        str(self.user_id),
                        tracking_url,
                        account_email,
                        account_password
                    )

                store_name = (
                    final_data
                    .get("cart", {})
                    .get("store_name", "DoorDash Order")
                )

                await send_order_success_webhook(
                    user_id=str(self.user_id),
                    store_name=store_name,
                    total_cents=self.cost_cents,
                    tracking_url=tracking_url,
                    email=account_email or "N/A",
                    password="REDACTED"
                )

                # -----------------------------------------
                # STAFF CHANNEL
                # Don't post the password into Discord.
                # -----------------------------------------
                staff_channel = interaction.client.get_channel(
                    STAFF_CHANNEL_ID
                )
                if staff_channel is None:
                    try:
                        staff_channel = (
                            await interaction.client.fetch_channel(
                                STAFF_CHANNEL_ID
                            )
                        )
                    except Exception as e:
                        print(
                            "[STAFF CHANNEL ERROR] "
                            f"{e}"
                        )

                if staff_channel:
                    staff_embed = discord.Embed(
                        title="  DoorDash Order Placed",
                        color=discord.Color.green()
                    )
                    staff_embed.add_field(
                        name="Job ID",
                        value=f"`{self.job_id}`",
                        inline=False
                    )
                    staff_embed.add_field(
                        name="Customer",
                        value=f"<@{self.user_id}>",
                        inline=False
                    )
                    if account_email:
                        staff_embed.add_field(
                            name="Account Email",
                            value=f"`{account_email}`",
                            inline=False
                        )
                    if account_password: # Added password to staff channel
                        staff_embed.add_field(
                            name="Account Password",
                            value=f"`{account_password}`",
                            inline=False
                        )
                    if order_uuid:
                        staff_embed.add_field(
                            name="Order UUID",
                            value=f"`{order_uuid}`",
                            inline=False
                        )
                    if tracking_url:
                        staff_embed.add_field(
                            name="Tracker",
                            value=tracking_url,
                            inline=False
                        )
                    try:
                        await staff_channel.send(
                            embed=staff_embed
                        )
                    except Exception as e:
                        print(
                            "[STAFF SEND ERROR] "
                            f"{e}"
                        )

                # -----------------------------------------
                # CUSTOMER ONLY GETS TRACKER
                # -----------------------------------------
                if tracking_url:
                    embed = discord.Embed(
                        title="  Order Successfully Placed!",
                        description=(
                            f"  **[Track Your Order]"
                            f"({tracking_url})**"
                        ),
                        color=discord.Color.green()
                    )
                else:
                    embed = discord.Embed(
                        title="  Order Successfully Placed!",
                        description=(
                            "Your order was successfully placed."
                        ),
                        color=discord.Color.green()
                    )

                await interaction.followup.send(
                    embed=embed,
                    ephemeral=True
                )
                return

            # ---------------------------------------------
            # UNKNOWN
            # ---------------------------------------------
            if payment_status in [
                "verifying",
                "verifying_long",
                "unverified"
            ]:
                await interaction.followup.send(
                    (
                        "  Your order was submitted, but "
                        "DoorDash is still confirming it. "
                        "Please wait while the order status "
                        "finishes updating."
                    ),
                    ephemeral=True
                )
                return

            # ---------------------------------------------
            # REAL FAILURE
            # ---------------------------------------------
            card_error = final_data.get("card_error")
            place_error = final_data.get("place_order_error")
            generic_error = final_data.get("error")
            reason = None
            
            if isinstance(card_error, dict):
                reason = card_error.get("message")
            if (
                not reason
                and isinstance(place_error, dict)
            ):
                reason = place_error.get("message")
            if not reason:
                if isinstance(generic_error, dict):
                    reason = generic_error.get("message")
                elif generic_error:
                    reason = str(generic_error)

            if not reason:
                if payment_status == "declined":
                    reason = "Payment was declined."
                elif payment_status == "failed":
                    reason = "DoorDash could not place the order."
                else:
                    reason = "Order could not be confirmed."

            await log_order(
                self.job_id,
                str(self.user_id),
                self.cost_cents,
                "failed"
            )

            await interaction.followup.send(
                f"  Order failed: `{reason}`",
                ephemeral=True
            )

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.red
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This prompt is not yours.",
                ephemeral=True
            )
            return

        if self.clicked:
            await interaction.response.send_message(
                "  Action locked.",
                ephemeral=True
            )
            return

        async with aiohttp.ClientSession() as session:
            await woolix.cancel_job(
                session,
                self.job_id
            )

        await interaction.response.edit_message(
            content="  Order draft cancelled.",
            embed=None,
            view=None
        )