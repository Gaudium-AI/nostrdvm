import json
import os

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nostr_utils import get_referenced_event_by_id, get_event_by_id
from nostr_sdk import Tag

"""
This File contains a Module to summarize Text, based on a prompt using a the HuggingChat LLM on Huggingface

Accepted Inputs: Prompt (text)
Outputs: Generated text
"""


class TextSummarizationHuggingChat(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_SUMMARIZE_TEXT
    TASK: str = "summarization"
    FIX_COST: float = 0
    dependencies = [("nostr-dvm", "nostr-dvm"),
                    ("hugchat", "hugchat")]

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)
        super().__init__(name, dvm_config, nip89config, admin_config, options)

    def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "event" and input_type != "job" and input_type != "text":
                    return False

        return True

    def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}
        prompt = ""

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    prompt = tag.as_vec()[1]
                elif input_type == "event":
                    evt = get_event_by_id(tag.as_vec()[1], client=client, config=dvm_config)
                    prompt = evt.content()
                elif input_type == "job":
                    evt = get_referenced_event_by_id(event_id=tag.as_vec()[1], client=client,
                                                     kinds=[EventDefinitions.KIND_NIP90_RESULT_EXTRACT_TEXT,
                                                            EventDefinitions.KIND_NIP90_RESULT_SUMMARIZE_TEXT,
                                                            EventDefinitions.KIND_NIP90_RESULT_TRANSLATE_TEXT,
                                                            EventDefinitions.KIND_NIP90_RESULT_CONTENT_DISCOVERY],
                                                     dvm_config=dvm_config)
                    if evt is None:
                        print("Event not found")
                        raise Exception
                    
                    if evt.kind() == EventDefinitions.KIND_NIP90_RESULT_CONTENT_DISCOVERY:
                        result_list = json.loads(evt.content())
                        prompt = ""
                        for tag in result_list:
                            e_tag = Tag.parse(tag)
                            evt = get_event_by_id(e_tag.as_vec()[1], client=client, config=dvm_config)
                            prompt += evt.content() + "\n"

                    else:
                        prompt = evt.content()
        options = {
            "prompt": prompt,
        }
        request_form['options'] = json.dumps(options)

        return request_form

    def process(self, request_form):
        from hugchat import hugchat
        from hugchat.login import Login
        sign = Login(os.getenv("HUGGINGFACE_EMAIL"), os.getenv("HUGGINGFACE_PASSWORD"))
        cookie_path_dir = "./cookies_snapshot"
        try:
            cookies = sign.loadCookiesFromDir(
                cookie_path_dir)  # This will detect if the JSON file exists, return cookies if it does and raise an Exception if it's not.
        except:
            cookies = sign.login()
            sign.saveCookiesToDir(cookie_path_dir)


        options = DVMTaskInterface.set_options(request_form)

        try:
            chatbot = hugchat.ChatBot(cookies=cookies.get_dict())  # or cookie_path="usercookies/<email>.json"
            query_result = chatbot.query("Summarize the following text in maximum 5 sentences: " + options["prompt"])
            print(query_result["text"])  # or query_result.text or query_result["text"]
            return str(query_result["text"]).lstrip()

        except Exception as e:
            print("Error in Module: " + str(e))
            raise Exception(e)



# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = build_default_config(identifier)
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I use a LLM connected via Huggingchat",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {}
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return TextSummarizationHuggingChat(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                     admin_config=admin_config)


if __name__ == '__main__':
    process_venv(TextSummarizationHuggingChat)
