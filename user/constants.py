def get_integration_code_snippet(token: str) -> str:
    integration_code_snippet = f"""
    1) Paste the following script tag at the very top of the <head> of your site, replacing [SCRIPT] and [/SCRIPT] with the appropriate tag brackets:
    <br><br>
    [SCRIPT] type="text/javascript" src="https://pub-97c89484d63d47cd8329552fff50e010.r2.dev/main.js" defer[/SCRIPT]
    <br><br>
    Install the @pingbase/connect package using npm or yarn:
    <br>
    npm install --save @pingbase/connect
    <br>
    (or)
    <br>
    yarn install --save @pingbase/connect
    <br><br>
    2) Add the following command in your code to initialise PingBase
    <br><br>
    import PingBase from '@pingbase/connect';
    <br><br>
    PingBase('initOrg', '{token}');
    <br>
    PingBase('initUser', 'email', 'firstName', 'lastName', 'trialType');
    """
    return integration_code_snippet


PINGBASE_BOT = "Pingbase Bot"


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
