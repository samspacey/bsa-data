export interface SampleReview {
  id: number;
  sentiment: "positive" | "negative";
  title: string;
  rating: string;
  date: string;
  quote: string;
  context: string;
}

export const sampleReviews: SampleReview[] = [
  { id: 14, sentiment: "negative", title: "App is outdated and keeps logging me out", rating: "2/5", date: "Mar 2026", quote: "I've been trying to log in for three days. The app keeps asking for re-authentication and the fingerprint login stopped working after the last update. I'd expect better in 2026.", context: "App · Digital experience" },
  { id: 22, sentiment: "positive", title: "Lovely staff at the Newport branch",      rating: "5/5", date: "Feb 2026", quote: "Rebecca on the counter remembered me from my last visit. That kind of service is impossible to find at the big banks.", context: "Branch · Service" },
  { id: 27, sentiment: "negative", title: "Savings rates aren't competitive",         rating: "2/5", date: "Feb 2026", quote: "Looked at their rates and they're half a percent below what I can get elsewhere. Loyalty doesn't pay.", context: "Savings · Rates" },
  { id: 31, sentiment: "positive", title: "Mortgage process was refreshingly human",  rating: "5/5", date: "Jan 2026", quote: "Our advisor actually listened. She spotted an error on our application we hadn't noticed and fixed it before submission.", context: "Mortgage · Experience" },
  { id: 35, sentiment: "negative", title: "Branch hours have been cut again",         rating: "2/5", date: "Jan 2026", quote: "The branch closes at 3pm now. That's useless if you work. Feels like they're pushing us online.", context: "Branch · Access" },
  { id: 41, sentiment: "positive", title: "Local touch matters",                      rating: "5/5", date: "Dec 2025", quote: "They sponsor the local carnival every year. That community presence is why I've stayed thirty years.", context: "Community" },
];

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  cites?: number[];
}

export const sampleConversation: Record<string, ChatMessage[]> = {
  loyalist: [
    { role: "assistant", text: "Oh, hello there. Are you from Monmouthshire? How lovely. I've been a member for longer than I care to admit - do sit down. I always enjoy having a chat about the society." },
    { role: "user", text: "Hi Margaret - thanks for making time. How have you been finding things lately?" },
    { role: "assistant", text: "Well, truthfully, I'm a little worried. They've shortened the hours at my branch in Abergavenny again. Tuesdays and Thursdays close at three now. It sounds small but when you've organised your week around popping in on a Thursday afternoon for thirty years, it matters.", cites: [35] },
    { role: "user", text: "That sounds frustrating. Do the staff there know you?" },
    { role: "assistant", text: "Oh yes. Eirwen knew my husband, God rest him, and she always asks after the grandchildren. That's why I go - it's not just banking, it's a little social outing. I'd hate for that to go.", cites: [22, 41] },
    { role: "user", text: "What do you make of their savings rates?" },
    { role: "assistant", text: "Well, my son keeps telling me I could get more elsewhere. He sends me these comparison websites. But I'd rather a half-percent less and know the people I'm dealing with, honestly.", cites: [27] },
  ],
  digital: [
    { role: "assistant", text: "Hey - yeah, happy to talk. I've been with the society about eighteen months now. Picked them over Monzo for my first mortgage because a friend said the service was properly human. So… early verdict: yes on the service, meh on the tech." },
  ],
  family: [
    { role: "assistant", text: "Hi - yes, got ten minutes between school pickup and tea. The mortgage is up for renewal in August which is already giving me ulcers. And we've got the kids' savings accounts with you too, so there's a lot riding on this relationship right now." },
  ],
  business: [
    { role: "assistant", text: "Good to meet you. I've run the engineering firm in Kendal for twenty-two years and banked with the society for most of them. Personal and business. That matters - I don't want to be speaking to a different person every time the phone rings." },
  ],
};

export const suggestedPrompts: Record<string, string[]> = {
  loyalist: [
    "If your daughter asked where to put her savings, would you say us? Honestly?",
    "Tell me about the last time you walked out of the branch annoyed.",
    "If we closed Abergavenny tomorrow, what would that actually mean to you?",
    "What do you talk about at bingo when the society comes up?",
    "Read me the last letter we sent you - what did you make of it?",
  ],
  digital: [
    "If the app broke for a week, would you still stay?",
    "When did you last recommend us - and what did you actually say?",
    "What do our competitors do that we don't?",
    "Describe the sign-up flow in three honest words.",
  ],
  family: [
    "Walk me through the moment you chose us for the mortgage.",
    "What would make you move everything elsewhere?",
    "How does the remortgage process compare to last time?",
    "What do you wish we offered for the kids?",
  ],
  business: [
    "If your relationship manager left tomorrow, would you leave too?",
    "What does 'good service' actually mean for a business like yours?",
    "Tell me about a decision we got wrong for you.",
    "What would make you bring more of your business to us?",
  ],
};

export const screensaverQuotes = [
  { q: "The branch closes at 3pm now. That's useless if you work. Feels like they're pushing us online.", who: "Margaret, 74", where: "Newport branch · member since 1989", societyId: "monmouthshire" },
  { q: "Our advisor actually listened. She spotted an error on our application we hadn't noticed and fixed it before submission.", who: "Sarah, 42", where: "Remortgage · 2026", societyId: "yorkshire" },
  { q: "Loyalty doesn't pay. Their rates are half a percent below what I can get elsewhere.", who: "Rhys, 29", where: "App review · Feb 2026", societyId: "nationwide" },
  { q: "It's not just banking. It's a little social outing.", who: "Beryl, 81", where: "On her weekly branch visit", societyId: "cumberland" },
];
