# Variable constants
PINGBASE_BOT = "Pingbase Bot"
BANNER_OOO_TEXT = "Your status has been automatically set to busy as the time is now outside of team office hours. To receive calls, change your status to active:"
BANNER_OOO_HYPERLINK_TEXT = "Change"

# CheckIn Feature variables
SKIPPED = "skipped"
NOT_APPLICABLE = "not_applicable"
COMPLETED = "completed"
PENDING = "pending"

# CheckIn events

CHECKIN_SKIPPED = "CHECKIN_SKIPPED"
CHECKIN_COMPLETED = "CHECKIN_COMPLETED"
CHECKIN_NOT_APPLICABLE = "CHECKIN_NOT_APPLICABLE"


# Session
SESSION_RECORDING = "SESSION_RECORDING"


# Function constants
def get_integration_code_snippet(token: str) -> str:
    integration_code_snippet = f"""
    1) Paste the following script tag at the very top of the <head> of your site, replacing [SCRIPT] and [/SCRIPT] with the appropriate tag brackets:
    <br><br>
    [SCRIPT] type="text/javascript" src="https://pub-97c89484d63d47cd8329552fff50e010.r2.dev/voice/main.js" defer[/SCRIPT]
    <br><br>
    Install the @pingbase/connect package using npm or yarn:
    <br>
    npm install @pingbase/connect
    <br>
    (or)
    <br>
    yarn install @pingbase/connect
    <br><br>
    2) Add the following command in your code to initialise PingBase
    <br><br>
    import PingBaseVoice from '@pingbase/connect/PingBaseVoice';
    <br>
    PingBaseVoice("initOrg", "ORG_TOKEN")
    <br><br>
    PingBase('initOrg', '{token}');
    <br>
    PingBase('initUser', 'phone');
    <br><br>
    for more details visit <a href="https://docs.pingbase.ai/voice-widget-integration">Docs</a>
    """
    return integration_code_snippet


def get_new_app_signup_slack_block_template_part_1():
    return (
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": ":tada: \t *New Signup \t:tada:*"},
        },
    )


def get_new_app_signup_slack_block_template_part_2(company, email):
    return (
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Company:*\n{company}\n*Email:*\n{email}",
            },
            "accessory": {
                "type": "image",
                "image_url": "https://api.slack.com/img/blocks/bkb_template_images/approvalsNewDevice.png",
                "alt_text": "computer thumbnail",
            },
        },
    )


def get_new_app_signup_slack_block_template_part_3():
    return (
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Awesome :rose:",
                        "emoji": True,
                    },
                    "style": "primary",
                    "value": "click_me_123",
                    "url": "https://api.pingbase.ai/admin/user/organization/",
                },
            ],
        },
    )


def get_first_enduser_invite_slack_block_template_part_1(company):
    return (
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":tada: \t *First Enduser for {company} \t:tada:*",
            },
        },
    )


def get_first_enduser_invite_slack_block_template_part_2(email, phone):
    return (
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Email:*\n{email} \n *Phone:*\n{phone}",
            },
            "accessory": {
                "type": "image",
                "image_url": "https://media3.giphy.com/media/gfZUYT3ReSiaF28bnn/giphy_s.gif?cid=6c09b952cbmd0knfetng27dxz54cyjc3wkwold0ue99xlols&ep=v1_internal_gif_by_id&rid=giphy_s.gif&ct=s",
                "alt_text": "Yes!!!",
            },
        },
    )


def get_first_enduser_invite_slack_block_template_part_3():
    return (
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": ":rose: Awesome :rose:",
                        "emoji": True,
                    },
                    "style": "primary",
                    "value": "click_me_1234",
                    "url": "https://api.pingbase.ai/admin/user/end-users/",
                },
            ],
        },
    )
