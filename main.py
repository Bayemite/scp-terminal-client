# TODO: nav forward/backward thru url history
# TODO-Feature: suggestions for user: close matches when nav-ing using 'open' or 'access'
# TODO: collapsible P linkaables

# dbSearch- searchs for tag/phrase
# http://www.scpwiki.com/scp-4450/offset/1


# In-builts
try:
    import readline  # For smart input()'s for GNU
except ImportError:
    pass
import shutil
import textwrap
import shlex
import time
import urllib.parse

from io import BytesIO
import os

####

# Third-party
import requests
from bs4 import BeautifulSoup

import rich
import rich.console  # Cause rich doesn't the sub thingys for some reason
import rich.rule  ##

import tkinter as tk
from PIL import ImageTk
from PIL import Image
####

# Own
import markup

####

parser = "html5lib"

linkable_attr = "data-linkable"

scp_classes = {
    "Safe": "bold green",
    "Euclid": "yellow",
    "Keter": "bold red",
    "Thaumiel": "gray",
    "Neutralized": "gray",
}

custom_theme = rich.theme.Theme(
    {
        "link-style": "bold blue",
        "rule-style": "white on black",
        "em-style": "italic bold green",
        "bold-style": "bold yellow",
    }
)


def print_exit():
    rich.print("\n[bold green]Exit.[/]\n")


# Returns three digits code of digits (1 -> 001, 45 -> 045)
# Numbers bigger than three digits are left unchanged
# ValueError for negative numbers
def three_digit(num: int) -> str:
    if num < 0:
        raise ValueError("Negative numbers cannot be converted to three digit code.")
    if num < 10:
        return f"00{num}"
    elif num < 100:
        return f"0{num}"
    else:
        return str(num)


def remove_unwanted(content: BeautifulSoup) -> None:
    unwanted = content.find_all(attrs={"class": "page-rate-widget-box"})
    if unwanted:
        for i in unwanted:
            i.decompose()
    unwanted = content.find_all(attrs={"class": "footer-wikiwalk-nav"})
    if unwanted:
        for i in unwanted:
            i.decompose()

    unwanted = content.find_all(attrs={"style": "display:none"})
    if unwanted:
        for i in unwanted:
            i.decompose()

    unwanted = content.find_all(attrs={"class", "licensebox"})
    if unwanted:
        for i in unwanted:
            i.decompose()


# Use as callback in BeautifulSoup find/find_all functions to find all linkables (links, imgs)
# See convert_linkables for more
def is_linkable(tag):
    return tag.has_attr(linkable_attr)


# Get rid of markup/add markup to the linkable
def linkable_style(string: str, add_style: bool = True):
    if add_style:
        return f"[link-style]<{string}>[/]"
    else:
        return rich.text.Text.from_markup(string).plain[1:-1]


def convert_linkables(soup: BeautifulSoup, content: BeautifulSoup) -> None:
    
    # Open collapsibles data are removed as unwanted 'style="display: none"' tags
    collapsibles_closed = content.find(attrs={"class": "collapsible-block-folded"})
    if collapsibles_closed:
        new_tag = soup.new_tag("p")
        i = 0
        for block in collapsibles_closed:
            if block.string:
                new_tag.string = linkable_style(block.string)
            else:
                new_tag.string = linkable_style(f"ANON-SECTION-{i}")
                i += 1

            block.replace_with(new_tag)

    links = content.find_all('a')
    if links:
        i = -1
        for link in links:
            i += 1
            if not link.string:
                continue
            temp = linkable_style(link.string)
            link.string.replace_with(temp)

            link[linkable_attr] = 'link'

    imgs = content.find_all("img")
    if imgs:
        tag = soup.new_tag('a')
        for i, img in enumerate(imgs):          
            tag.string = linkable_style(f"IMG-{i}")
            tag["href"] = img['src']
            tag[linkable_attr] = 'img'
            img.replace_with(tag)


def convert_for_terminal(soup: BeautifulSoup, content: BeautifulSoup) -> None:

    convert_linkables(soup, content)

    bolds = content.find_all("strong")
    if bolds:
        for bold in bolds:
            if bold.string:
                bold.string.replace_with(f"[bold-style]{bold.string}[/]")

    ems = content.find_all("em")
    if ems:
        for em in ems:
            if em.string:
                em.string.replace_with(f"[em-style]{em.string}[/]")

    h_rules = content.find_all("hr")
    if h_rules:
        line_tag = soup.new_tag("p")
        line_tag.string = markup.tag.rule
        for hr in h_rules:
            hr.replace_with(line_tag)

    ctr_style = (
        lambda tag: tag.has_attr("style") and "text-align: center" in tag["style"]
    )
    centers = content.find_all(ctr_style)
    if centers:
        for c in centers:
            for d in c.children:
                if d.string:
                    d.string.replace_with(markup.tag.center + d.string)

    


def create_help_table():
    return [
        """
[bold-style]help:[/] help <topic>
Help for various topics and commands.

[blue]Options[/]
  <topic>=<syntax|navigation>
    = An optional help topic.

""",
        """
[bold-style]access:[/] access <id>
Access the SCP logfile specified.
""",
        """
[bold-style]open:[/] open <tag>
Access a link in the current logfile.
Section tags are denoted by blue <...> tokens.

[blue]Options[/]
  <tag> = An tag: the full string contained within the <...> tags.
             May be an image, link to another log, or a collapsed section.
             
""",
        """
[bold-style]exit:[/]
Exit the session.
""",
        """
[bold-style]cls:[/]
Clear the screen.
""",
    ]


# None if no title found
def page_title(soup: BeautifulSoup) -> str:
    title = ""
    tag = soup.find(attrs={"id": "page-title"})
    if tag:
        title = tag.string.strip()
    return title


def get_content(soup: BeautifulSoup):
    return soup.find(attrs={"id": "page-content"})


# Returns None on failure
# Else returns whole BeautifulSoup obj
def print_page(url: str, console: rich.console.Console) -> BeautifulSoup:
    try:
        response = requests.get(url)
    except requests.ConnectionError as e:
        print(f"Connection error: {e.strerror}")
    soup = BeautifulSoup(response.text, parser)

    for string in soup.strings:
        string.replace_with(rich.markup.escape(string))
    content = get_content(soup)
    if not content:
        print(f"Could not find content.")
        return None

    remove_unwanted(content)
    convert_for_terminal(soup, content)

    title = page_title(soup)

    print("\n\n")
    console.rule(style="rule-style")
    console.print(f"[rule-style]{title}[/]", justify="center")
    console.rule(style="rule-style")

    wrap_text = lambda text: textwrap.fill(
        line,
        shutil.get_terminal_size().columns - 10,
        initial_indent=" " * 5,
        subsequent_indent=" " * 5,
    )

    for line in content.get_text().splitlines():

        for scp_class, color in scp_classes.items():
            line = line.replace(scp_class, f"[{color}]{scp_class}[/]")

        if markup.tag.rule in line:
            console.rule(style="rule-style")
            console.print("\n")
        elif markup.tag.center in line:
            line = wrap_text(line)
            try:
                console.print(line, justify="center", end="\n\n")
            except Exception:
                pass
        else:
            line = wrap_text(line)
            try:
                console.print(line, end="\n\n")
            except Exception:
                pass
        # time.sleep(0.05)
        # input()

    print("\n\n")
    console.rule(style="rule-style")
    console.print(f"[rule-style]END OF LOG[/]", justify="center")
    console.rule(style="rule-style")
    print("\n\n")
    
    return soup


class NavInfo:
    def __init__(self):
        self.url = ""
        self.content = None
        self.title_path = []
        self.url_path = []
        self.url_history = []

    # Soup can be None to indicate a unsucessful url request- everything is ignored
    def update(self, url: str, soup: BeautifulSoup, clear_path: bool = False):
        if soup:
            self.content = get_content(soup)
            self.url = url
            self.url_history.append(url)
            if clear_path:
                self.url_path.clear()
                self.title_path.clear()
            self.url_path.append(url)
            self.title_path.append(page_title(soup))
        else:
            self.content = None
            self.url = None


def open_cmd(args, console: rich.console.Console, info: NavInfo) -> None:
    if len(args) != 2:
        print("Usage: open <tag>\n")
    elif not info.url:
        print(f"Not in a logfile. Cannot open '{args[1]}'.\n")
    else:
        links = info.content.find_all(is_linkable)
        if not links:
            print("No openable links found.\n")
        else:
            found = False
            for link in links:
                if link.string and args[1] == linkable_style(link.string, False):
                    if (
                        not link.has_attr("href")
                        or link["href"]
                        == "javascript:;"  # Misc. doesn't work for HTML requests
                    ):
                        continue
                    
                    url = urllib.parse.urljoin(info.url, link["href"])
                    if link[linkable_attr] == 'img':
                        name = args[1]
                        print(f"Opening {name}.")
                        root = tk.Tk(className=name)
                        root.resizable(False, False)
                        r = requests.get(url)
                        img = Image.open(BytesIO(r.content))
                        tk_img = ImageTk.PhotoImage(img)
                        label = tk.Label(root, image=tk_img)
                        label.pack()
                        label.image = tk_img
                        root.mainloop()
                        found = True
                        print("Closed image.\n")
                    else:
                        soup = print_page(url, console)
                        info.update(url, soup)
                        if soup:
                            found = True
                            break
            if not found:
                print("No openable links found.\n")


def access_cmd(args, console: rich.console.Console, info: NavInfo):
    print_error = lambda: print("Usage: access <id>\n")
    if len(args) == 2:
        try:
            scp_num = int(args[1])
            if scp_num < 0:
                print("Need non-negative id.\n")
        except ValueError:
            print_error()
        else:
            scp_num = three_digit(scp_num)
            url = f"http://www.scpwiki.com/scp-{scp_num}"
            soup = print_page(url, console)
            info.update(url, soup, True)
    else:
        print_error()


def main():
    help_table = create_help_table()
    console = rich.console.Console(highlight=False, theme=custom_theme)
    info = NavInfo()

    error_msg = lambda: print("Unknown command. Try 'help'.\n")

    while True:
        st = ""
        st = input(f"{'/'.join(info.title_path)}> ")
        try:
            args = shlex.split(st)
        except ValueError:
            error_msg()
            continue
        if len(args) == 0:
            continue
        elif args[0] == "help":
            for i in sorted(help_table):
                console.print(i)
        elif args[0] == "open":
            open_cmd(args, console, info)
        elif args[0] == "cls":
            os.system("cls" if os.name == "nt" else "clear")
        elif args[0] == "access":
            access_cmd(args, console, info)
        elif args[0] == "exit":
            print_exit()
            return
        else:
            error_msg()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_exit()
