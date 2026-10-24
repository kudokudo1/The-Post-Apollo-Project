# WhatsApp personal-account adapter // Work package A feasibility gate

**Status: BLOCKED / RESEARCH.** This is a truthful blocker, **not** a native adapter implementation and **not** proof that WhatsApp personal messaging is impossible forever.

## Verified access routes (2026-10-24)

- The documented **WhatsApp Business Platform / Cloud API** is business-account messaging for businesses communicating with their customers, not a general personal WhatsApp account inbox. Official product info: <https://whatsappbusiness.com/resources/faq/>.
- WhatsApp's published consumer terms and responsible-use guidelines warn against unauthorized access, reverse engineering, scraping and automated account activity. Sources: <https://www.whatsapp.com/legal/terms-of-service>, <https://faq.whatsapp.com/361005896189245/>.
- A third-party WhatsApp Web automation or unofficial reverse-engineered protocol is **not** accepted here as a safe or supported personal-account integration.

## Consequence for Post-Apollo

- Keep the existing **WhatsApp // Native integration pending** Social menu slot unchanged.
- Do not create an adapter that falsely reports READY or invents conversations/send success.
- Do not request QR sessions, authentication secrets, contact exports or personal data.
- An official WhatsApp Business integration could be designed as a **separate**, explicitly approved product scope. It would not fulfill the user's personal chat goal automatically.

## Resume condition

The operator/integration owner must establish a documented, platform-authorized personal-account access path for reading and sending the user's conversations, with suitable account security and tested client support. Only then implement `WhatsAppAdapter.qml`, a service-specific bridge, and mocked plus live tests as required by v1.0.

**Ownership:** This blocker is service-scoped to `services/messaging/bridges/whatsapp/` and does not modify another worker's files or the shared UI.
