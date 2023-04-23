# needed a replacement for the suggested, but not working options: why not do a stupid request and parese the resutling page?
# Taken fron https://codefather.tech/blog/youtube-search-python/ and expanded.
def directSearch(input):
    import urllib.request
    import re

    search_keyword = input.replace(" ", "+")
    html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + search_keyword)
    video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
    result = "https://www.youtube.com/watch?v=" + video_ids[0]
    print("result:", result)

directSearch("bach jauchzet frohlocket")
# result: https://www.youtube.com/watch?v=DlwcZT1XVss - which works
