import asyncio
from patchright.async_api import async_playwright

async def login_to_doordash(page, email: str, password: str) -> bool:
    print(f"[Support Bot] Loading DoorDash account for {email}...")

    WOOSH_EXTENSION_ID = "gchkidccanmmjfknmjcimbfjnkjemhdo"

    try:
        # --------------------------------------------------
        # OPEN DOORDASH FIRST
        # --------------------------------------------------

        await page.goto(
            "https://www.doordash.com",
            wait_until="domcontentloaded",
            timeout=30000
        )

        await page.wait_for_timeout(2000)

        # --------------------------------------------------
        # OPEN WOOSH EXTENSION
        # --------------------------------------------------

        print("[Support Bot] Opening Woosh extension...")

        extension_page = await page.context.new_page()

        possible_pages = [
            f"chrome-extension://{WOOSH_EXTENSION_ID}/popup.html",
            f"chrome-extension://{WOOSH_EXTENSION_ID}/index.html",
            f"chrome-extension://{WOOSH_EXTENSION_ID}/",
        ]

        extension_open = False

        for extension_url in possible_pages:
            try:
                await extension_page.goto(
                    extension_url,
                    wait_until="domcontentloaded",
                    timeout=5000
                )

                await extension_page.wait_for_timeout(1000)

                body_text = await extension_page.locator(
                    "body"
                ).inner_text()

                if body_text.strip():
                    extension_open = True

                    print(
                        "[Support Bot] Woosh extension opened."
                    )

                    break

            except Exception:
                continue

        if not extension_open:
            print(
                "[Support Bot Login Error]: "
                "Woosh extension is not loaded in this "
                "Patchright browser."
            )

            try:
                await extension_page.close()
            except Exception:
                pass

            return False

        # --------------------------------------------------
        # MAKE EXTENSION EASY TO USE MANUALLY
        # --------------------------------------------------

        try:
            await extension_page.bring_to_front()
        except Exception:
            pass

        print("")
        print("========================================")
        print("[Support Bot] WOOSH ACCOUNT LOAD")
        print(f"[Support Bot] Find: {email}")
        print("[Support Bot] Select Red app")
        print("[Support Bot] Click Load")
        print("========================================")
        print("")

        # --------------------------------------------------
        # WAIT FOR ACCOUNT TO BE LOADED
        # --------------------------------------------------

        print(
            "[Support Bot] Waiting for you to load "
            "the account in Woosh..."
        )

        # Give you up to 60 seconds to click Load.
        for attempt in range(60):

            await page.wait_for_timeout(1000)

            try:
                await page.bring_to_front()

                await page.reload(
                    wait_until="domcontentloaded",
                    timeout=10000
                )

                # Look for the public Sign In button.
                sign_in = page.locator(
                    "button:has-text('Sign In'), "
                    "a:has-text('Sign In')"
                )

                visible_sign_in = False
                count = await sign_in.count()

                for i in range(count):
                    candidate = sign_in.nth(i)

                    try:
                        if await candidate.is_visible(
                            timeout=200
                        ):
                            box = await candidate.bounding_box()

                            if box and box["y"] < 180:
                                visible_sign_in = True
                                break

                    except Exception:
                        continue

                # If the top Sign In disappeared,
                # the saved session probably loaded.
                if not visible_sign_in:

                    print(
                        "[Support Bot] DoorDash session "
                        "appears to be loaded."
                    )

                    try:
                        await extension_page.close()
                    except Exception:
                        pass

                    await page.bring_to_front()

                    return True

            except Exception:
                pass

            # Put Woosh back in front every few seconds.
            if attempt % 5 == 4:
                try:
                    await extension_page.bring_to_front()
                except Exception:
                    pass

        print(
            "[Support Bot Login Error]: "
            "Timed out waiting for Woosh account load."
        )

        return False

    except Exception as e:
        print(
            f"[Support Bot Login Error]: {e}"
        )

        return False

async def automate_missing_items(email: str, password: str):
    """
    Opens DoorDash in a persistent Chromium profile with
    the Woosh extension installed.

    Woosh/Discord login and the saved Chromium profile persist
    between runs.

    The Woosh account selection itself is done manually.
    """

    from pathlib import Path
    from patchright.async_api import async_playwright

    # Password is no longer used for the DoorDash login here.
    _ = password

    # ==========================================================
    # SETTINGS
    # ==========================================================

    PROFILE_DIR = Path.cwd() / "woosh_browser_profile"

    WOOSH_EXTENSION_PATH = (
        r"C:\Users\itzac\Downloads\WoolixSessionExtension"
    )

    print("")
    print("==========================================")
    print("[Support Bot] Starting Woosh browser")
    print(f"[Support Bot] Account: {email}")
    print(f"[Support Bot] Profile: {PROFILE_DIR}")
    print("==========================================")
    print("")

    try:

        async with async_playwright() as p:

            # ==================================================
            # START PERSISTENT CHROMIUM
            # ==================================================

            print(
                "[Support Bot] Starting persistent Chromium..."
            )

            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),

                headless=False,

                viewport={
                    "width": 1280,
                    "height": 800
                },

                args=[
                    f"--disable-extensions-except={WOOSH_EXTENSION_PATH}",
                    f"--load-extension={WOOSH_EXTENSION_PATH}",
                ],
            )

            # ==================================================
            # GET/CREATE TAB
            # ==================================================

            if context.pages:
                page = context.pages[0]
            else:
                page = await context.new_page()

            try:

                # ==============================================
                # OPEN DOORDASH
                # ==============================================

                print("[Support Bot] Opening DoorDash...")

                await page.goto(
                    "https://www.doordash.com",
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                await page.wait_for_timeout(3000)

                print("")
                print("==========================================")
                print("[Support Bot] WOOSH ACCOUNT LOAD")
                print("")
                print(f"TARGET ACCOUNT:")
                print(f"    {email}")
                print("")
                print("1. Click the Woosh extension icon.")
                print("")
                print(
                    "2. If Woosh says 'Continue with Discord',"
                )
                print(
                    "   click it and finish the Discord login."
                )
                print("")
                print("3. Open Woosh again if it closes.")
                print("")
                print("4. Select: Red app")
                print("")
                print(
                    f"5. Find this account: {email}"
                )
                print("")
                print("6. Click Load.")
                print("")
                print(
                    "DO NOT close the Chromium window."
                )
                print("==========================================")
                print("")

                # ==============================================
                # IMPORTANT
                #
                # DO NOTHING TO THE DOORDASH TAB WHILE THE
                # USER IS USING THE EXTENSION.
                #
                # Calling page.bring_to_front(), reload(), goto(),
                # etc. would close the extension popup.
                # ==============================================

                print(
                    "[Support Bot] Waiting 120 seconds "
                    "for Woosh..."
                )

                print(
                    "[Support Bot] The bot will NOT touch "
                    "the browser during this time."
                )

                # 2 minutes for:
                # - Discord login on first run
                # - reopening Woosh
                # - selecting Red app
                # - finding email
                # - clicking Load
                await page.wait_for_timeout(120000)

                # ==============================================
                # CHECK DOORDASH AFTER WOOSH LOAD
                # ==============================================

                print(
                    "[Support Bot] Checking DoorDash session..."
                )

                await page.bring_to_front()

                await page.reload(
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                await page.wait_for_timeout(4000)

                # ==============================================
                # CHECK WHETHER TOP-RIGHT SIGN IN STILL EXISTS
                # ==============================================

                sign_in_visible = False

                try:

                    sign_in_buttons = page.locator(
                        "button:has-text('Sign In'), "
                        "a:has-text('Sign In')"
                    )

                    count = await sign_in_buttons.count()

                    for i in range(count):

                        candidate = sign_in_buttons.nth(i)

                        try:

                            if not await candidate.is_visible(
                                timeout=300
                            ):
                                continue

                            box = await candidate.bounding_box()

                            if not box:
                                continue

                            # Top navigation Sign In
                            if box["y"] < 180:

                                sign_in_visible = True

                                break

                        except Exception:
                            continue

                except Exception as e:

                    print(
                        "[Support Bot] Session check warning: "
                        f"{e}"
                    )

                # ==============================================
                # STILL LOGGED OUT
                # ==============================================

                if sign_in_visible:

                    print("")
                    print("==========================================")
                    print("[Support Bot Login Error]")
                    print("")
                    print(
                        "DoorDash still appears logged out."
                    )
                    print("")
                    print(
                        "Make sure you clicked Load on the "
                        "correct RED APP account in Woosh."
                    )
                    print("")
                    print(
                        "If Woosh asked for Discord login, "
                        "finish that first, reopen Woosh, "
                        "then click Load."
                    )
                    print("==========================================")
                    print("")

                    # Leave browser open so you can inspect it.
                    await page.wait_for_timeout(30000)

                    return

                # ==============================================
                # SESSION LOADED
                # ==============================================

                print("")
                print("==========================================")
                print(
                    "[Support Bot] DoorDash session loaded!"
                )
                print(f"[Support Bot] Account: {email}")
                print("==========================================")
                print("")

                # ==============================================
                # OPEN ORDERS
                # ==============================================

                print(
                    "[Support Bot] Opening DoorDash orders..."
                )

                await page.goto(
                    "https://www.doordash.com/orders",
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                await page.wait_for_timeout(5000)

                print(
                    "[Support Bot] DoorDash orders page opened."
                )

                # ==============================================
                # YOUR LEGITIMATE POST-LOGIN SUPPORT CODE
                # CAN CONTINUE BELOW HERE.
                # ==============================================

                print(
                    "[Support Bot] Browser is ready."
                )

                # Keep it open for inspection/use.
                await page.wait_for_timeout(30000)

            except Exception as e:

                print(
                    f"[Support Bot Error]: {e}"
                )

                try:
                    await page.wait_for_timeout(15000)
                except Exception:
                    pass

            finally:

                # ==============================================
                # SAVE PROFILE
                #
                # Closing a persistent context keeps:
                #
                # - Woosh Discord login
                # - extension storage
                # - Chromium cookies
                # - local storage
                # - saved browser profile
                #
                # DO NOT DELETE woosh_browser_profile.
                # ==============================================

                print(
                    "[Support Bot] Saving persistent "
                    "browser profile..."
                )

                try:
                    await context.close()
                except Exception:
                    pass

    except Exception as e:

        print(
            f"[Support Bot Browser Error]: {e}"
        )