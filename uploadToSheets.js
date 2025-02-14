const { google } = require("googleapis");
const fs = require("fs");
const path = require("path");

// Load your Google credentials JSON file
const CREDENTIALS_PATH = "C:/Users/Olivia Croteau/Downloads/gsCredentials.json"; // Update with your actual JSON key file name
const SPREADSHEET_ID = "14KErbuI8nk2_69MdvU0Qycdm4kuWlfsAWehyy2F3ZEw"; // Get this from the URL of your Google Sheet

async function uploadJSONToSheet() {
  try {
    // Authenticate with Google
    const auth = new google.auth.GoogleAuth({
      keyFile: CREDENTIALS_PATH,
      scopes: ["https://www.googleapis.com/auth/spreadsheets"],
    });

    const sheets = google.sheets({ version: "v4", auth });

    // Read JSON file
    const jsonFilePath = "C:/Users/Olivia Croteau/AppData/Roaming/electron/processing/processedJson/Medyka-Shehyni_Feb-05-2025Processed/result.json"; // Replace with your JSON file
    const jsonData = JSON.parse(fs.readFileSync(jsonFilePath, "utf8"));

    // ✅ Extract base sheet name from "name" key
    let baseSheetName = jsonData.name;
    if (!baseSheetName) {
      throw new Error("Invalid JSON format: 'name' key is missing.");
    }

    // ✅ Append current datetime (YYYY-MM-DD_HH-MM)
    const now = new Date();
    const formattedDate = now.toISOString().replace(/T/, " ").replace(/:/g, "-").split(".")[0]; // Format: "2025-02-12 14-30"
    const sheetName = `${baseSheetName} ${formattedDate}`;

    // ✅ Ensure sheet name is within the 100-character limit
    if (sheetName.length > 100) {
      sheetName = sheetName.substring(0, 100);
    }

    // *** Extract the messages array ***
    const messages = jsonData.messages;  // ✅ NEW: Accessing the messages array

    // Check if messages exist
    if (!messages || !Array.isArray(messages)) {
      throw new Error("Invalid JSON format: 'messages' array is missing or not an array.");
    }

    // ✅ Create a new sheet with the extracted name
    await sheets.spreadsheets.batchUpdate({
      spreadsheetId: SPREADSHEET_ID,
      resource: {
        requests: [
          {
            addSheet: {
              properties: { title: sheetName },
            },
          },
        ],
      },
    });

    console.log(`✅ New sheet "${sheetName}" created.`);

    // Convert JSON into a 2D array
    const headers = ["id", "date", "date_unixtime", "from", "text", "reply_id", "LANGUAGE", "TRANSLATED_TEXT"]; // ✅ Define required fields
    const values = messages.map((msg) => headers.map((header) => msg[header] || "")); // ✅ Extract only necessary fields
    // Prepare data for Sheets API
    const requestBody = {
      values: [headers, ...values], // Include headers as the first row
    };

    // Upload data to Google Sheets
    await sheets.spreadsheets.values.update({
      spreadsheetId: SPREADSHEET_ID,
      range: `${sheetName}!A1`, // Start from cell A1
      valueInputOption: "RAW",
      resource: requestBody,
    });

    console.log("Data uploaded successfully!");
  } catch (error) {
    console.error("Error uploading data:", error);
  }
}

// Run the function
uploadJSONToSheet();

