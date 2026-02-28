from __future__ import annotations

"""
Hybrid AI Agent – DOM reader.

Playwright-based DOM extraction for structured perception.

Responsibilities:
- Attach to or create a Playwright Page
- Walk the DOM and extract a compact list of interesting elements
- Return a JSON-like dict structure that EnvironmentNormaliser can consume
"""

from typing import Any, Dict, List, Optional

from playwright.async_api import Browser, Page, Playwright, async_playwright


class DomReader:
    """
    Asynchronous DOM reader built on Playwright.

    Usage patterns:
    - Call `read(url=...)` to open a page and extract elements.
    - Or navigate elsewhere first (via another component) and call `read()`
      with no URL to just snapshot the current page.

    Returned structure (simplified):
    {
        "url": "...",
        "title": "...",
        "elements": [
            {
                "selector": "css selector",
                "tag": "button",
                "text": "Submit",
                "disabled": false,
                "role": "button" | null,
            },
            ...
        ],
    }
    """

    def __init__(self, headless: bool = False) -> None:
        self._headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    async def _ensure_page(self) -> Page:
        """
        Ensure a Playwright page exists. Lazily starts Playwright and a
        Chromium browser if needed.
        """
        if self._page is not None:
            return self._page

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        self._page = await self._browser.new_page()
        return self._page

    async def attach_page(self, page: Page) -> None:
        """
        Attach an existing Playwright Page created elsewhere.

        This allows sharing the same browser/page between the executor
        and the structured perception layer if desired.
        """
        self._page = page

    async def close(self) -> None:
        """Close any owned browser and stop Playwright."""
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        self._page = None

    async def read(self, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Capture a lightweight snapshot of the current page DOM.

        If `url` is provided, this method will navigate to that URL first.
        The returned dict is intentionally small and tailored for
        EnvironmentNormaliser, not a full HTML dump.
        """
        page = await self._ensure_page()

        if url is not None:
            await page.goto(url, wait_until="domcontentloaded")

        elements: List[Dict[str, Any]] = await self._extract_elements(page)

        title = await page.title()
        result: Dict[str, Any] = {
            "url": page.url,
            "title": title,
            "elements": elements,
        }
        return result

    async def _extract_elements(self, page: Page) -> List[Dict[str, Any]]:
        """
        Run JavaScript in the page to collect interesting elements.

        We focus on likely-interactive elements plus headings/text that
        often serve as anchors: buttons, inputs, links, and elements with
        ARIA roles. Each element includes:
        - tag: lowercased tag name
        - text: trimmed innerText (capped length)
        - disabled: boolean
        - role: ARIA role if any
        - selector: a reasonably stable CSS selector
        """

        script = """
        () => {
            function cssPath(el) {
                if (!(el instanceof Element)) return null;
                const path = [];
                while (el && el.nodeType === Node.ELEMENT_NODE) {
                    let selector = el.nodeName.toLowerCase();
                    if (el.id) {
                        selector += '#' + CSS.escape(el.id);
                        path.unshift(selector);
                        break;
                    } else {
                        let sib = el;
                        let nth = 1;
                        while (sib = sib.previousElementSibling) {
                            if (sib.nodeName === el.nodeName) nth++;
                        }
                        selector += `:nth-of-type(${nth})`;
                    }
                    path.unshift(selector);
                    el = el.parentElement;
                }
                return path.join(' > ');
            }

            const nodes = Array.from(
                document.querySelectorAll(
                    'a, button, input, textarea, select, [role=\"button\"], [role=\"link\"], [role=\"checkbox\"], [role=\"menuitem\"]'
                )
            );

            const elements = nodes.map((el) => {
                const tag = el.tagName.toLowerCase();
                const text = (el.innerText || el.value || '').trim().slice(0, 200);
                const disabled = !!(el.disabled || el.getAttribute('aria-disabled') === 'true');
                const role = el.getAttribute('role');
                const selector = cssPath(el);
                return {
                    tag,
                    text,
                    disabled,
                    role,
                    selector,
                };
            });

            return elements;
        }
        """

        raw_elements: List[Dict[str, Any]] = await page.evaluate(script)
        return raw_elements

