const bot = BotManager.getCurrentBot();
const API_URL = "http://192.168.0.39:4242/";

function onMessage(msg) {
  
  // const replyMessage = "room: " + msg.room + "\n"
  // replyMessage += "channelId: " + msg.channelId + "\n"
  // replyMessage += "msg: " + msg.content + "\n"
  // replyMessage += "isDebugRoom: " + msg.isDebugRoom + "\n"
  // replyMessage += "isGroupChat: " + msg.isGroupChat + "\n"
  // replyMessage += "sender: " + msg.author.name + "\n"
  // replyMessage += "senderHash: " + msg.author.hash + "\n"
  // replyMessage += "isMention: " + msg.isMention + "\n"
  // replyMessage += "packageName: " + msg.packageName + "\n"
  // msg.reply(replyMessage);

  const data = {
    room: msg.room,
    channelId: msg.channelId.toString(),
    content: msg.content,
    isDebugRoom: msg.isDebugRoom,
    isGroupChat: msg.isGroupChat,
    sender: msg.author.name,
    senderHash: msg.author.hash,
    isMention: msg.isMention,
    packageName: msg.packageName,
    logId: msg.logId.toString()
  };

  let response = org.jsoup.Jsoup.connect(API_URL + "onMessage")
    .header("Content-Type", "application/json")
    .requestBody(JSON.stringify(data))
    .ignoreContentType(true)
    .ignoreHttpErrors(true)
    .timeout(1000 * 60 * 10)
    .post();
  
  const json = JSON.parse(response.text());
  if (json.status === "success" && json.is_reply) {
    msg.reply(json.message.content);
  }
}
bot.addListener(Event.MESSAGE, onMessage);


/**
 * (string) msg.content: 메시지의 내용
 * (string) msg.room: 메시지를 받은 방 이름
 * (User) msg.author: 메시지 전송자
 * (string) msg.author.name: 메시지 전송자 이름
 * (Image) msg.author.avatar: 메시지 전송자 프로필 사진
 * (string) msg.author.avatar.getBase64()
 * (boolean) msg.isDebugRoom: 디버그룸에서 받은 메시지일 시 true
 * (boolean) msg.isGroupChat: 단체/오픈채팅 여부
 * (string) msg.packageName: 메시지를 받은 메신저의 패키지명
 * (void) msg.reply(string): 답장하기
 * (string) msg.command: 명령어 이름
 * (Array) msg.args: 명령어 인자 배열
 */
function onCommand(msg) {
  
}
bot.setCommandPrefix("!help");
bot.addListener(Event.COMMAND, onCommand);


function onCreate(savedInstanceState, activity) {
  var textView = new android.widget.TextView(activity);
  textView.setText("Hello, World!");
  textView.setTextColor(android.graphics.Color.DKGRAY);
  activity.setContentView(textView);
}

function onStart(activity) {}

function onResume(activity) {}

function onPause(activity) {}

function onStop(activity) {}

function onRestart(activity) {}

function onDestroy(activity) {}

function onBackPressed(activity) {}

bot.addListener(Event.Activity.CREATE, onCreate);
bot.addListener(Event.Activity.START, onStart);
bot.addListener(Event.Activity.RESUME, onResume);
bot.addListener(Event.Activity.PAUSE, onPause);
bot.addListener(Event.Activity.STOP, onStop);
bot.addListener(Event.Activity.RESTART, onRestart);
bot.addListener(Event.Activity.DESTROY, onDestroy);
bot.addListener(Event.Activity.BACK_PRESSED, onBackPressed);