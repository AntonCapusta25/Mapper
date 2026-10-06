/**
 * NexusScrape - Google Apps Script (GAS) Mailer Webhook
 * Version: 2.0 (CRM & Tracking Enhanced)
 */

function doGet(e) {
  return ContentService.createTextOutput("NexusScrape CRM Webhook is Active").setMimeType(ContentService.MimeType.TEXT);
}

function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
    var action = payload.action || "send";

    if (action === "checkReplies") {
       return checkReplies();
    }

    var leads = payload.leads;       
    var subject = payload.subject;   
    var body = payload.body;         
    var vpsIp = payload.vps_ip || "178.104.45.251:8000";

    if (!leads || leads.length === 0) {
      return responseJSON({status: "error", message: "No leads provided"});
    }

    var threadMap = {};
    var sentCount = 0;

    for (var i = 0; i < leads.length; i++) {
      var lead = leads[i];
      if (!lead.email) continue;
      
      // 1. Personalize template
      var pBody = body.replace(/{{name}}/g, lead.name || "Bedrijf")
                      .replace(/{{companyName}}/g, lead.name || "Bedrijf");
      
      // 2. Inject Tracking Pixel
      var trackingUrl = "http://" + vpsIp + "/api/track/" + lead.id;
      var htmlBody = pBody + '<img src="' + trackingUrl + '" width="1" height="1" style="display:none;" />';
      
      // 3. Plain Text Fallback
      var plainBody = pBody.replace(/<[^>]*>?/gm, ' ').trim();
      
      // 4. Send & Capture Thread ID
      // Using createDraft + send to ensure we get the message/thread object back
      var draft = GmailApp.createDraft(lead.email, subject, plainBody, {
        htmlBody: htmlBody,
        name: "Oleksandr | Homemade",
        replyTo: "nederland@homemademeals.net"
      });
      var sentMsg = draft.send();
      threadMap[lead.email] = sentMsg.getThread().getId();
      
      sentCount++;
    }

    return responseJSON({
      status: "success", 
      message: sentCount + " tracked emails sent.",
      threadMap: threadMap
    });

  } catch (error) {
    return responseJSON({status: "error", message: error.toString()});
  }
}

function checkReplies() {
  // Simple logic: find threads where last message is FROM lead, not ME
  var threads = GmailApp.search('is:unread label:inbox "nederland@homemademeals.net"', 0, 20);
  var replies = [];
  
  for (var i = 0; i < threads.length; i++) {
    var thread = threads[i];
    var messages = thread.getMessages();
    var lastMsg = messages[messages.length - 1];
    
    if (!lastMsg.isFromMe()) {
      replies.push({
        threadId: thread.getId(),
        from: lastMsg.getFrom(),
        subject: thread.getFirstMessageSubject(),
        body: lastMsg.getPlainBody(),
        date: lastMsg.getDate()
      });
    }
  }
  
  return responseJSON({status: "success", replies: replies});
}

function responseJSON(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function doOptions(e) {
  return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
}
