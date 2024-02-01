import cloudscraper
from bs4 import BeautifulSoup
import json

with open("low_terms.txt", "r") as file:
    urls = [row for row in file]

scraper = cloudscraper.create_scraper()

results = []

counter = 0
for url in urls:
    counter += 1
    print(f"=========={counter}=============")
    # if counter >10:
    #     break
    # time.sleep(0.5)
    res = scraper.get(url)
    if res.status_code == 200:
        soup = BeautifulSoup(res.content, 'html.parser')
        title = soup.find('h1').get_text(strip=True)
        dd_elements = soup.find('dd').contents
        definition_full = soup.find('dd').get_text(' ', strip=True)
        print(f"----------{title}-------------")

        definition = ""
        origin = ""
        compare = ""
        enumerations = {}
        current_number = None
        sub_definition_text = ""
        found_compare = False
        current_sub_term = None
        references = {}
        is_no_simbols = True
        is_no_tags = True
        num = 0

        for element in dd_elements:  ###### if only :
            if element.name == 'b':
                if element.get_text(strip=True) != ":":
                    is_no_simbols = False

            if element.name != None and element.name != "br":
                is_no_tags = False

        for element in dd_elements:
            if element.name == 'b':
                b_text = element.get_text(strip=True)
                if not b_text.isalpha() and b_text != ":":
                    if current_number is not None:
                        if sub_definition_text:
                            if current_sub_term:
                                enumerations[current_number]["sub_terms"][
                                    current_sub_term] += sub_definition_text.strip()
                            else:
                                enumerations[current_number]["definition"] += sub_definition_text.strip()
                        sub_definition_text = ""
                    current_number = b_text
                    enumerations[current_number] = {"definition": "", "sub_terms": {}, "note": "", "compares": "",
                                                    "see also": ""}
                    current_sub_term = None

                elif b_text.isalpha() and len(b_text) == 1 and current_number is not None:
                    if current_sub_term and sub_definition_text:
                        enumerations[current_number]["sub_terms"][current_sub_term] += sub_definition_text.strip()
                    elif not current_sub_term and sub_definition_text:
                        index_colon = sub_definition_text.find(':')
                        index_triple_space = sub_definition_text.find('   ')

                        if index_colon == -1 and index_triple_space == -1:
                            first_index = len(sub_definition_text)
                        else:
                            indexes = [index for index in [index_colon, index_triple_space] if index != -1]
                            first_index = min(indexes) if indexes else len(sub_definition_text)

                        enumerations[current_number]["definition"] = sub_definition_text[:first_index]

                    current_sub_term = b_text
                    enumerations[current_number]["sub_terms"][current_sub_term] = ""
                    sub_definition_text = ""


                elif not b_text.isalpha() and b_text == ":" and is_no_simbols:
                    sub_term_1 = ""
                    if element.find_all_previous('br'):
                        for br in element.find_all_previous('br'):  ###
                            next_sibling = br.nextSibling.nextSibling
                            if next_sibling and next_sibling.name == 'b' and next_sibling.get_text() == ':':
                                sub_term_1 = next_sibling.nextSibling
                                break
                    else:
                        sub_term_1 = element.nextSibling
                    num += 1
                    current_number = str(num)
                    current_sub_term = "1"

                    if sub_term_1 and isinstance(sub_term_1, str):
                        if sub_term_1.strip():
                            enumerations[current_number] = {current_sub_term: sub_term_1.strip()}
                        else:
                            if element.nextSibling.nextSibling.name == 'a':
                                enumerations[current_number] = {
                                    current_sub_term: element.nextSibling.nextSibling.get_text(strip=True)}
                    current_sub_term = None

            if is_no_tags:
                num += 1
                if element.get_text().strip() != "":
                    definition = element.get_text().strip()
                current_sub_term = None

            if element.name == 'i' and current_number is not None:
                current_text = element.get_text(strip=True)

                if "NOTE" in current_text:
                    clear_notes = current_text[5:]
                    enumerations[current_number]["note"] = clear_notes

                origin_match_1 = definition_full.find('[')
                origin_1 = ""
                if origin_match_1 != -1:
                    origin_end_1 = definition_full.find(']', origin_match_1 + 1)
                    origin_1 = definition_full[origin_match_1:origin_end_1 + 1].strip() if origin_end_1 != -1 else ""

                if element.nextSibling.get_text() and element.nextSibling.get_text() not in origin_1:
                    next_text = element.nextSibling.get_text(strip=True)
                    if len(next_text) > 10:
                        next_text = next_text[2:-2] if next_text[0] == ',' else next_text
                        enumerations[current_number][element.get_text(strip=True)] = next_text

            if element.name == 'a':
                link_text = element.get_text(strip=True)
                references[link_text] = element.get('href')

                if current_number is not None:
                    prev_sibling = element.previous_sibling

                    if current_number is not None:
                        if "compare" in prev_sibling:
                            enumerations[current_number]["compares"] = link_text
                        elif "see also" in prev_sibling:
                            enumerations[current_number]["see also"] = link_text

            if isinstance(element, str) and current_number is not None:
                sub_definition_text += element.strip()

            for element in dd_elements:
                if soup.find('b'):
                    if found_compare and soup.find('b').contents != [':']:
                        break
                if element.name == 'a' and found_compare:
                    compare = element.get_text(strip=True)
                    break
                if 'compare' in str(element):
                    found_compare = True

        num = 0

        if current_number is not None and sub_definition_text and not is_no_simbols:
            if current_sub_term:
                enumerations[current_number]["sub_terms"][current_sub_term] += sub_definition_text.strip()
            else:
                enumerations[current_number]["definition"] += sub_definition_text.strip()

        colon_pos = definition_full.find(':')
        if colon_pos != -1:
            next_delimiter_pos = min(
                [pos for pos in [definition_full.find(c, colon_pos + 1) for c in [',', '(', ':']] if pos != -1],
                default=len(definition_full))
            definition = definition_full[colon_pos + 1:next_delimiter_pos].strip()

        origin_match = definition_full.find('[')
        if origin_match != -1:
            origin_end = definition_full.find(']', origin_match + 1)
            origin = definition_full[origin_match:origin_end + 1].strip() if origin_end != -1 else ""

        entry = {"definition": definition} if definition else {"definition": title}
        if origin:
            entry["origin"] = origin
        if compare:
            entry["compare"] = compare

        names = ["definition", "sub_terms", "note", "compares", "see also"]
        if not is_no_simbols:
            for num, sub_def in enumerations.items():
                for name in names:
                    if not sub_def[name]:
                        del sub_def[name]
                enumerations[num] = sub_def

        if enumerations:
            filtered_enumerations = {k: v for k, v in enumerations.items() if v}
            entry["sub_definitions"] = filtered_enumerations

        entry["references"] = references

        results.append({title: entry})

        ###
        json_data = json.dumps(results[-1], indent=4, ensure_ascii=False)
        print(json_data)
        file_name = url.split('/')[-1].split('.')[0]

        with open(f"data/{file_name}.json", "w") as file:
            file.write(json_data)

    else:
        print(f"Error: {url} Status {res.status_code}")

json_data = json.dumps(results, indent=4, ensure_ascii=False)

with open("low.json", "w") as file:
    file.write(json_data)