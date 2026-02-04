// script.js - replace your existing file with this

// Helper: get element by id (safe)
const $ = id => document.getElementById(id);

// ----------------- Analyze (file upload) -----------------
document.getElementById("upload-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = $("file");
    if (!fileInput || !fileInput.files.length) {
        alert("Please choose a file to upload.");
        return;
    }

    const fd = new FormData();
    fd.append("file", fileInput.files[0]);

    // optional: show loader
    const loader = $("loader");
    if (loader) loader.style.display = "block";

    try {
        const res = await fetch("/analyze", { method: "POST", body: fd });
        const data = await res.json();

        if (loader) loader.style.display = "none";

        if (data.error) {
            alert("Analyze error: " + data.error);
            return;
        }

        // fill UI fields (match your HTML ids)
        $("summary").textContent = data.summary || data.original || "No text extracted.";
        // case nature & risk_score naming depends on your backend — adapt if needed:
        $("case-nature").textContent = data.case_nature || data.classification || "Not detected";
        $("risk-score").textContent = data.risk_score || data.risk || "N/A";
        $("punishments").textContent = data.punishments || "Not available";
// NEW: show legal insights
if ($("ipc-sections")) $("ipc-sections").textContent = (data.ipc_sections || []).join("\n");
if ($("remedies")) $("remedies").textContent = (data.remedies || []).join("\n");
if ($("lawyers")) $("lawyers").textContent = (data.lawyers || []).join("\n");

// ----------------- Show Similar Cases -----------------


        // clear previous translation/chat
        if ($("translation")) $("translation").textContent = "";
        if ($("chat-answer")) $("chat-answer").textContent = "";

    } catch (err) {
        if (loader) loader.style.display = "none";
        console.error(err);
        alert("Failed to analyze document. See console for details.");
    }
});

// ----------------- Translate -----------------
// ----------------- Translate -----------------
document.getElementById("translate-btn").addEventListener("click", async () => {
    const summaryEl = $("summary");
    const text = summaryEl ? summaryEl.textContent.trim() : "";

    if (!text) {
        alert("No summary / text available to translate. Run Analyze first.");
        return;
    }

    const langEl = $("language");
    const targetLang = langEl ? langEl.value : "hi";

    // SHOW TRANSLATE LOADER
    const tloader = $("translate-loader");
    if (tloader) tloader.style.display = "block";

    try {
        const res = await fetch("/translate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text, target_lang: targetLang })
        });

        const json = await res.json();

        if (!res.ok) {
            $("translation").textContent = "Translation error: " + (json.error || res.statusText);
            return;
        }

        $("translation").textContent = json.translated_text || json.translated || "";

    } catch (err) {
        console.error("Translate fetch failed:", err);
        $("translation").textContent = "Translation failed (network or server).";
    }

    // HIDE TRANSLATE LOADER
    if (tloader) tloader.style.display = "none";
});

// ----------------- Chatbot (keeps your existing route) -----------------
document.getElementById("ask-btn").addEventListener("click", async () => {
    const question = $("question").value?.trim();
    const docText = $("summary")?.textContent || "";

    if (!question) {
        alert("Please type a question first.");
        return;
    }
    try {
        const res = await fetch("/chatbot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question, text: docText })
        });
        const json = await res.json();
        $("chat-answer").textContent = json.answer || json.response || "No answer.";
    } catch (err) {
        console.error(err);
        $("chat-answer").textContent = "Chatbot unavailable.";
    }
});

// ----------------- Download (optional) -----------------
// ===============================
// Download PDF Report
// ===============================
document.getElementById("download-btn").addEventListener("click", async () => {
    const data = {
        summary: $("summary").innerText,
        case_nature: $("case-nature").innerText,
        risk_score: $("risk-score").innerText,
        punishments: $("punishments").innerText,
        ipc_sections: $("ipc-sections").innerText,
        remedies: $("remedies").innerText,
        lawyers: $("lawyers").innerText,
        
    };

    const response = await fetch("/download-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });

    if (!response.ok) {
        alert("Failed to generate PDF!");
        return;
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "Legal_Report.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();

    window.URL.revokeObjectURL(url);
});