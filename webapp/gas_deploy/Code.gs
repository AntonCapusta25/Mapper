/**
 * NexusScrape - Google Apps Script (GAS) Mailer Webhook
 * 
 * INSTRUCTIONS:
 * 1. Go to https://script.google.com/ and create a new project.
 * 2. Paste this code into Code.gs.
 * 3. Click "Deploy" -> "New deployment".
 * 4. Choose type: "Web app".
 * 5. Execute as: "Me".
 * 6. Who has access: "Anyone".
 * 7. Click Deploy, authorize the permissions, and copy the Web App URL.
 * 8. Paste the Web App URL into the NexusScrape Dashboard!
 */

function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
    var leads = payload.leads;       // Array of leads: [{email, name, ...}]
    var subject = payload.subject;   // Email Subject 
    var body = payload.body;         // Text/HTML body (use {{name}} for merging)

    if (!leads || leads.length === 0) {
      return ContentService.createTextOutput(JSON.stringify({status: "error", message: "No leads provided"}));
    }

    var sentCount = 0;

    for (var i = 0; i < leads.length; i++) {
      var lead = leads[i];
      if (!lead.email) continue;
      
      // Personalize the template
      var personalizedBody = body.replace(/{{name}}/g, lead.name || "Bedrijf");
      
      // Send Native Google Workspace Email
      GmailApp.sendEmail(lead.email, subject, personalizedBody, {
        htmlBody: personalizedBody,
        name: "Alex | Homemade"
      });
      
      sentCount++;
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "success", 
      message: sentCount + " emails sent natively via Google Workspace."
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error", 
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// Keep this to handle preflight HTTP checks from some environments
function doOptions(e) {
  return ContentService.createTextOutput("")
    .setMimeType(ContentService.MimeType.TEXT);
}
