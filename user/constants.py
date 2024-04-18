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
