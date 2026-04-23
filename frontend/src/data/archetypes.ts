export interface Archetype {
  id: string;
  name: string;
  initials: string;
  age: string;
  blurb: string;
  detail: string;
  concerns: string[];
  firstName: string;
  tone: "navy" | "coral" | "mint" | "sand";
}

export const archetypes: Archetype[] = [
  {
    id: "loyalist",
    name: "The Loyalist",
    initials: "ML",
    age: "70–80",
    blurb: "Retired; member for thirty-odd years. Knows the staff by name. Values the branch, the newsletter, and a proper conversation.",
    detail: "Uses the Newport branch weekly. Doesn't trust the app. Cares about staff continuity and the society's roots.",
    concerns: ["Branch closures", "Digital push", "Service quality"],
    firstName: "Margaret",
    tone: "navy",
  },
  {
    id: "digital",
    name: "The Digital Native",
    initials: "RM",
    age: "25–35",
    blurb: "Tech professional, first-time buyer. Chose a mutual over a bank for a reason - but expects the experience to match.",
    detail: "Signed up within the last year. Has opinions about the app, the signup flow, and notification rates.",
    concerns: ["Outdated tech", "Slow processes", "Rate competitiveness"],
    firstName: "Rhys",
    tone: "coral",
  },
  {
    id: "family",
    name: "The Family Juggler",
    initials: "SP",
    age: "38–48",
    blurb: "Working parent, mortgage holder, children's savings accounts. Time-poor but engaged.",
    detail: "Mortgage coming up for renewal. Manages the household finances. Wants clarity, not cleverness.",
    concerns: ["Remortgage rates", "Kids' savings", "Family security"],
    firstName: "Sarah",
    tone: "mint",
  },
  {
    id: "business",
    name: "The Business Owner",
    initials: "JH",
    age: "45–60",
    blurb: "Runs a local business. Long-standing member. Values the relationship, expects service that reflects their complexity.",
    detail: "Both personal and business banking. Expects a named contact and proper judgement, not a call centre.",
    concerns: ["Business lending", "Relationship continuity", "Service quality"],
    firstName: "James",
    tone: "sand",
  },
];
