"""
Email Open Detector module for validating email opens based on user agent strings.
Ported from C# implementation to Python.
Blog Link: https://www.gmass.co/blog/false-opens-in-gmail/
C# implementation: https://claude.site/artifacts/254eabbc-1408-44db-b2a2-00e1e229a9c3
"""

class EmailOpenDetector:
    # Known bot user agents that should be filtered out
    KNOWN_BOT_AGENTS = {
        "HubSpot Connect",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246 Mozilla/5.0",
        "AHC/2.1",
        "Amazon CloudFront",
        "Barracuda Sentinel (EE)",
        "python-requests/2.26.0",
        "Python/3.9 aiohttp/3.8.1",
        "lua-resty-http/0.07 (Lua) ngx_lua/10012",
        "lua-resty-http/0.10 (Lua) ngx_lua/10019",
        "okhttp/4.10.0",
        "python-requests/2.27.1",
        "python-requests/2.28.0",
        "lua-resty-http/0.07 (Lua) ngx_lua/10024",
        "cortex/1.0",
        "Aloha/1 CFNetwork/1404.0.5 Darwin/22.3.0",
        "Dalvik/2.1.0 (Linux; U; Android 8.0.0; SM-G930V Build/R16NW)",
        "Java/17.0.2",
        "macOS/13.4 (22F66) dataaccessd/1.0",
        "Snap URL Preview Service; bot; snapchat; https://developers.snap.com/robots",
        "iOS/16.5.1 (20F75) dataaccessd/1.0",
        "Dalvik/2.1.0 (Linux; U; Android 8.1.0; SM-J327V Build/M1AJQ)",
        "W3C-checklink/4.5 [4.160] libwww-perl/5.823",
        "yarn/1.22.4 npm/? node/v16.20.0 linux x64",
        "Microsoft Office/16.0 (Windows NT 10.0; Microsoft Outlook 16.0.14931; Pro)",
        "Microsoft Office/16.0 (Windows NT 10.0; Microsoft Outlook 16.0.16327; Pro)",
        "Social News Desk RSS Scraper",
        "iOS/16.3.1 (20D67) dataaccessd/1.0",
        "facebookexternalua",
        "Jetty/9.4.42.v20210604",
        "Microsoft Exchange/15.20 (Windows NT 10.0; Win64; x64)",
        "Dalvik/2.1.0 (Linux; U; Android 8.1.0; LM-Q710(FGN) Build/OPM1.171019.019)",
        "iOS/15.7 (19H12) dataaccessd/1.0",
        "Wget/1.9.1",
        "Office 365 Connectors",
        "Java/1.8.0_265",
        "iOS/15.7.6 (19H349) dataaccessd/1.0",
        "iOS/16.5 (20F66) dataaccessd/1.0",
        "Dalvik/2.1.0 (Linux; U; Android 12; SM-G970U Build/SP1A.210812.016)",
        "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
        "Microsoft Office/16.0 (Windows NT 10.0; Microsoft Outlook 16.0.16227; Pro)",
        "python-requests/2.28.2",
        "SCMGUARD",
        "Apache-HttpClient/4.5.1 (Java/1.8.0_172)",
        "FeedBurner/1.0 (http://www.FeedBurner.com)"
    }

    # Valid email proxy identifiers
    VALID_EMAIL_PROXIES = {
        "googleimageproxy",
        "yahoomailproxy",
        "outlookimageproxy"
    }

    # Browser identifiers for validation
    BROWSER_IDENTIFIERS = {
        "chrome/",
        "firefox/",
        "safari/",
        "edge/",
        "opera/"
    }

    @staticmethod
    def is_valid_email_open(user_agent: str) -> bool:
        """
        Determine if an email open event is valid based on the user agent string.
        
        Args:
            user_agent (str): The user agent string to validate
            
        Returns:
            bool: True if the email open appears valid, False otherwise
        """
        if not user_agent or user_agent.isspace():
            return False

        # Check against exact known bot User Agents
        if user_agent in EmailOpenDetector.KNOWN_BOT_AGENTS:
            return False

        # Allow bare Mozilla/5.0
        if user_agent.strip().lower() == "mozilla/5.0":
            return True

        # Allow known email image proxies
        user_agent_lower = user_agent.lower()
        if any(proxy in user_agent_lower for proxy in EmailOpenDetector.VALID_EMAIL_PROXIES):
            return True

        # Check for unusual browser combinations
        if EmailOpenDetector._has_unusual_browser_combination(user_agent):
            return False

        # Basic browser checks for webmail opens
        if EmailOpenDetector._is_likely_browser(user_agent):
            return True

        return True  # If we haven't rejected it by now, allow it

    @staticmethod
    def _has_unusual_browser_combination(user_agent: str) -> bool:
        """
        Check if the user agent has unusual browser identifier combinations.
        
        Args:
            user_agent (str): The user agent string to check
            
        Returns:
            bool: True if unusual combinations are found, False otherwise
        """
        user_agent_lower = user_agent.lower()
        browser_count = sum(1 for identifier in EmailOpenDetector.BROWSER_IDENTIFIERS 
                          if identifier in user_agent_lower)
        
        if browser_count > 1:
            # Common legitimate combination: Chrome + Safari (WebKit)
            is_webkit_combination = "chrome/" in user_agent_lower and "safari/" in user_agent_lower
            return not is_webkit_combination

        return False

    @staticmethod
    def _is_likely_browser(user_agent: str) -> bool:
        """
        Check if the user agent appears to be from a legitimate browser.
        
        Args:
            user_agent (str): The user agent string to check
            
        Returns:
            bool: True if the user agent appears to be from a legitimate browser
        """
        user_agent_lower = user_agent.lower()

        # Check for mobile devices
        mobile_identifiers = ("iphone", "android", "ipad", "mobile")
        if any(ident in user_agent_lower for ident in mobile_identifiers):
            return True

        # Check for standard browser patterns
        mozilla_pattern = "mozilla/5.0" in user_agent_lower or "mozilla/4.0" in user_agent_lower
        browser_pattern = any(browser in user_agent_lower for browser in 
                            EmailOpenDetector.BROWSER_IDENTIFIERS.union({"msie", "trident/"}))

        return mozilla_pattern and browser_pattern 