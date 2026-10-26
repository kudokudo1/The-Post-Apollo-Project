# KakaoTalk personal-account integration feasibility

**Status:** BLOCKED / RESEARCH as a full Post-Apollo personal inbox.

**Reviewed:** 2026-10-26.

Official Kakao developer documentation exposes useful but narrower capabilities:

- Kakao Talk Social can retrieve KakaoTalk friends who are available to the
  developer application, subject to Kakao permission and user consent.
- Kakao Talk Message can send templated messages to the logged-in user's
  My Chatroom or to approved friends.
- Sending to friends requires additional feature permission, the `friends`
  / `talk_message` consent path, and is subject to provider quotas.
- The APIs do **not** expose the ordinary user's existing KakaoTalk chatroom
  history or an incoming personal-inbox stream.

Official references:

- https://developers.kakao.com/docs/en/kakaotalk-social/rest-api
- https://developers.kakao.com/docs/en/kakaotalk-message/rest-api
- https://developers.kakao.com/docs/en/kakaotalk-message/common
- https://pc.kakao.com/talk/notices/en?agent=win32
- https://pc.kakao.com/talk/notices/en?agent=mac

Kakao's official desktop clients are documented for Windows and macOS. No
official Linux KakaoTalk desktop client or full web inbox was verified.

## Post-Apollo decision

Do not create a fake `KakaoTalkAdapter.qml` that models a permissioned friend
list as real conversations or pretends outbound template sends provide message
history. That would violate the Shared Messaging Adapter Contract's requirement
to normalize real provider conversations/messages without fabrication.

A future separately scoped feature could investigate Kakao's **permissioned
outbound message/share** APIs as a limited capability. It must remain visibly
different from a full personal-chat backend and requires Kakao app approval,
OAuth consent, quota handling, and provider-policy review.

Until a supported full personal-inbox interface or official Linux client exists,
the Social KakaoTalk slot should remain an explicit provider-access blocker.
