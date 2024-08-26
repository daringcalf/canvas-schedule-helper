from datetime import timedelta
import json
import logging
import re
from bs4 import BeautifulSoup
import requests
import sys
from pathlib import Path
import readline  # https://stackoverflow.com/questions/7357007/python-raw-input-limit-with-mac-os-x-terminal

logging.basicConfig(level=logging.INFO)

canvas_base_url = "https://canvas.asu.edu/"


def sanitize_filename(filename):
    # Use only alphanumeric characters, hyphens, and underscores
    sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "_", filename)

    # Handle special filenames reserved by Windows, regardless of extension
    windows_reserved = ["CON", "PRN", "AUX", "NUL"] + [
        f"{name}{i}" for name in ["COM", "LPT"] for i in range(1, 10)
    ]
    if sanitized.upper() in windows_reserved:
        sanitized = "_" + sanitized

    # Shorten to 255 characters to ensure it's within common filesystem limits
    sanitized = sanitized[:255]

    return sanitized


def parse_course_page(course_page_html):
    soup = BeautifulSoup(course_page_html, "html.parser")
    modules = []

    for module_div in soup.find_all("div", class_="item-group-condensed"):
        media_guide_a = module_div.find(
            "a",
            title=lambda x: x
            and (x.startswith("Media Guide") or x.endswith("Media Guide")),
        )
        # if no media guide then it's not a module with lectures
        if media_guide_a is None:
            continue

        media_guide_link = media_guide_a["href"]
        if not media_guide_link.startswith("http"):
            media_guide_link = canvas_base_url + media_guide_link

        module_name = (
            module_div.find(
                "span",
                class_="collapse_module_link",
            )["title"]
            .split(":", 1)[1]
            .strip()
        )

        lectures = []

        for lecture_a in module_div.find_all(
            "a",
            title=lambda x: x and x.startswith("Lecture Playlist"),
            class_="ig-title",
        ):
            lecture_link = lecture_a["href"]
            if not lecture_link.startswith("http"):
                lecture_link = canvas_base_url + lecture_link
            lectures.append(
                {
                    "title": lecture_a["title"].split(":", 1)[1].strip(),
                    "link": lecture_link,
                }
            )

        modules.append(
            {
                "name": module_name,
                "mediaGuideUrl": media_guide_link,
                "lectures": lectures,
            }
        )

    return modules


def parse_lecture_page(lecture_page_html):
    download_suffix = "/download?download_frd=1"

    soup = BeautifulSoup(lecture_page_html, "html.parser")

    body = ""

    # Iterate through all <script> tags
    for script_tag in soup.find_all("script"):
        script_content = script_tag.string if script_tag.string else ""

        # Use regular expressions to find the ENV object inside script content
        match = re.search(r"ENV\s*=\s*(\{.*?\});", script_content, re.DOTALL)

        if match:
            env_content = match.group(1)
            try:
                env_dict = json.loads(env_content)
                body = env_dict["WIKI_PAGE"]["body"]
                break
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON: {e}")
                continue

    soup = BeautifulSoup(body, "html.parser")

    videos = []

    for transcript_a in soup.find_all("a", class_="instructure_file_link"):
        full_title = transcript_a.get("title", transcript_a.text.strip())

        if "." in full_title:
            transcript_type = full_title.split(".")[-1]
        else:
            transcript_type = "unknown"

        if transcript_type not in ["srt", "vtt", "unknown"]:
            continue

        if "." in full_title:
            title = ".".join(full_title.split(".")[:-1])
        else:
            title = full_title

        title = (
            title.replace("_Transcripts", "")
            .replace("_Transcript", "")
            .replace("_Transcipt", "")
            .replace("_transcripts", "")
            .replace("_transcript", "")
            .replace(" Transcript", "")
            .replace("Transcript", "")
            .strip()
        )

        link = transcript_a["href"]
        download_url = link.split("?")[0] + download_suffix

        videos.append(
            {
                "title": title,
                "transcript_type": transcript_type,
                "link": link,
                "download_url": download_url,
            }
        )

    return videos


def get_url_content(url, cookies):
    if cookies is None:
        raise ValueError("No cookies provided")

    logging.info(f"downloading... {url}")
    response = requests.get(url, headers={"Cookie": cookies})
    return response.text


def parse_last_timestamp(file_content, file_type):
    # raise error if file type is unexpected
    if file_type not in ["srt", "vtt", "unknown"]:
        raise ValueError(f"Unknown file type: {file_type}")

    # SRT timestamp format: 00:01:22,000 --> 00:01:24,400
    # VTT timestamp format: 00:01:22.000 --> 00:01:24.400
    # VTT timestamp format: 00:01:22,000 --> 00:01:24,400 (also found in some VTT files)
    time_pattern = re.compile(r"\d{2}:\d{2}:\d{2}[,|\.]\d{3}")
    timestamps = time_pattern.findall(file_content)

    if not timestamps:
        return None

    # Ensuring uniform format for conversion
    last_timestamp_str = timestamps[-1].replace(",", ".")

    # Split by colon to separate hours, minutes, and then seconds.milliseconds
    time_parts = last_timestamp_str.split(":")
    hours, minutes = int(time_parts[0]), int(time_parts[1])

    # For seconds and milliseconds, further split by dot
    seconds, milliseconds = [int(x) for x in time_parts[2].split(".")]

    last_duration = timedelta(
        hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds
    )
    return last_duration


def format_timedelta(td):
    """Utility function to format timedelta object into HH:MM:SS"""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def display_course_summary(course_modules):
    print("*** Course Durations ***")
    print(f"{'Module / Lecture / Video':<135} | {'Type':<8} | {'Duration':<10}")
    print("-" * 157)

    for module_idx, module in enumerate(course_modules, 1):
        module_duration = timedelta()

        for lecture in module.get("lectures", []):
            lecture_duration = timedelta()

            for video in lecture.get("videos", []):
                if video.get("length") is None:
                    continue
                lecture_duration += video.get("length", timedelta())

            module_duration += lecture_duration

        # Print module title with the total duration for the module
        module_title = f"Module {module_idx}: {module.get('name', 'Unnamed Module')}"
        print(
            f"{module_title:<135} | {'Module':<8} | {format_timedelta(module_duration):<10}"
        )

        for lecture_idx, lecture in enumerate(module.get("lectures", []), 1):
            lecture_duration = timedelta()

            for video in lecture.get("videos", []):
                if video.get("length") is None:
                    continue
                lecture_duration += video.get("length", timedelta())

            # Print lecture title with the total duration for the lecture
            lecture_title = f"  Lecture {lecture_idx}: {lecture['title']}"
            print(
                f"{lecture_title:<135} | {'Lecture':<8} | {format_timedelta(lecture_duration):<10}"
            )

            for video_idx, video in enumerate(lecture.get("videos", []), 1):
                if video.get("length") is None:
                    continue
                video_title = f"    Video {video_idx}: {video['title']}"
                print(
                    f"{video_title:<135} | {'Video':<8} | {format_timedelta(video['length']):<10}"
                )

        print("-" * 157)


def parse_arguments(args):
    """Extract arguments from command line input."""
    arguments = {}
    for arg in args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            arguments[key] = value
    return arguments


def main():
    args = parse_arguments(sys.argv[1:])
    course_id = args.get("course_id")

    while not course_id:
        course_id = input("Enter course ID: ").strip()

    cookies = input("Enter cookies: ").strip()
    while not cookies:
        answer = (
            input("No cookies provided, are you sure you want to continue? [y/n] ")
            .strip()
            .lower()
        )
        if answer.startswith("y"):
            break

        cookies = input("Enter cookies: ").strip()

    cache_dir = "cache"

    course_url = f"https://canvas.asu.edu/courses/{course_id}/modules"

    course_dir = Path(f"{cache_dir}/{course_id}")
    transcript_dir = course_dir / "subs"
    modules_page_path = course_dir / "modules.html"
    modules_page_html = ""

    if not transcript_dir.is_dir():
        logging.debug(f"Creating directory for course {course_id}")
        transcript_dir.mkdir(parents=True, exist_ok=True)

    modules_page_html_valid = False

    if modules_page_path.is_file():
        with open(modules_page_path, "r") as file:
            modules_page_html = file.read()

            if "Course Modules" in modules_page_html:
                modules_page_html_valid = True

    if not modules_page_html_valid:
        modules_page_html = get_url_content(course_url, cookies)

        if "Course Modules" not in modules_page_html:
            logging.error(
                "the downloaded modules page is not valid, maybe the cookies are expired."
            )
            exit()

        with open(modules_page_path, "w") as file:
            file.write(modules_page_html)

    course_modules = parse_course_page(modules_page_html)

    if not course_modules:
        sys.exit("No course modules found")

    for module in course_modules:
        for lecture in module.get("lectures", []):
            lecture_html = ""
            lecture_html_path = course_dir / sanitize_filename(
                f"{lecture.get('title')}.html"
            )

            # Check if the lecture HTML file is valid
            # if the file is not valid, download and save the HTML file
            lecture_html_valid = False

            if lecture_html_path.is_file():
                logging.info(f"cache found: {lecture_html_path}")
                with open(lecture_html_path, "r") as file:
                    lecture_html = file.read()
                    if "Lecture Playlist" in lecture_html:
                        lecture_html_valid = True
                    else:
                        logging.warning(
                            f'cached file "{lecture_html_path}" is not valid (Course ID: {course_id})'
                        )

            if not lecture_html_valid:
                lecture_html = get_url_content(lecture.get("link"), cookies)

                if "Lecture Playlist" not in lecture_html:
                    logging.error(
                        "the downloaded lecture page is not valid, maybe the cookies are expired."
                    )
                    exit()

                with open(lecture_html_path, "w", encoding="utf-8") as file:
                    file.write(lecture_html)

            lecture["videos"] = parse_lecture_page(lecture_html)

            for video in lecture.get("videos", []):
                transcript_content = ""
                transcript_path = transcript_dir / sanitize_filename(
                    sanitize_filename(
                        f"{video.get('title')}.{video.get('transcript_type')}"
                    )
                )
                if transcript_path.is_file():
                    with open(transcript_path, "r") as file:
                        transcript_content = file.read()
                else:
                    transcript_content = get_url_content(
                        video.get("download_url"), cookies
                    )
                    with open(transcript_path, "w") as file:
                        file.write(transcript_content)

                video["length"] = parse_last_timestamp(
                    transcript_content, video.get("transcript_type")
                )

    display_course_summary(course_modules)


if __name__ == "__main__":
    main()
