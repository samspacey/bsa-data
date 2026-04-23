import { useEffect, useState } from "react";
import { Screensaver } from "./pages/Screensaver";
import { SocietySelection } from "./pages/SocietySelection";
import { PersonaSelection } from "./pages/PersonaSelection";
import { ChatInterface } from "./pages/ChatInterface";
import { BenchmarkModal } from "./pages/BenchmarkModal";
import type { Society } from "./data/societies";
import type { Archetype } from "./data/archetypes";
import { resetSessionId, trackEvent } from "./api/analytics";

type Screen = "screensaver" | "society" | "persona" | "chat";

function App() {
  const [screen, setScreen] = useState<Screen>("screensaver");
  const [society, setSociety] = useState<Society | null>(null);
  const [persona, setPersona] = useState<Archetype | null>(null);
  const [benchmarkOpen, setBenchmarkOpen] = useState(false);

  // Auto-return to screensaver after long idle on the selection/persona screens.
  useEffect(() => {
    if (screen === "screensaver" || screen === "chat") return;
    const timer = window.setTimeout(() => setScreen("screensaver"), 180_000);
    const reset = () => {
      window.clearTimeout(timer);
    };
    window.addEventListener("pointerdown", reset, { once: true });
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("pointerdown", reset);
    };
  }, [screen]);

  if (screen === "screensaver") {
    return (
      <Screensaver
        onEnter={() => {
          // New journey -> new session id so analytics sees this as a distinct run.
          resetSessionId();
          trackEvent("screensaver_entered");
          setScreen("society");
        }}
      />
    );
  }

  if (screen === "society") {
    return (
      <SocietySelection
        onSelect={s => {
          trackEvent("society_selected", { societyId: s.id, props: { society_name: s.name } });
          setSociety(s);
          setScreen("persona");
        }}
      />
    );
  }

  if (screen === "persona" && society) {
    return (
      <PersonaSelection
        society={society}
        onBack={() => {
          trackEvent("navigated_back", { societyId: society.id, props: { from: "persona" } });
          setScreen("society");
        }}
        onSelect={a => {
          trackEvent("persona_selected", {
            societyId: society.id,
            persona: { id: a.id },
            props: { persona_name: a.name },
          });
          setPersona(a);
          setScreen("chat");
        }}
      />
    );
  }

  if (screen === "chat" && society && persona) {
    return (
      <>
        <ChatInterface
          society={society}
          persona={persona}
          onBack={() => {
            trackEvent("chat_exited", {
              societyId: society.id,
              persona: { id: persona.id },
            });
            setSociety(null);
            setPersona(null);
            setScreen("screensaver");
          }}
          onOpenBenchmark={() => {
            trackEvent("benchmark_opened", {
              societyId: society.id,
              persona: { id: persona.id },
            });
            setBenchmarkOpen(true);
          }}
        />
        {benchmarkOpen && (
          <BenchmarkModal
            society={society}
            onClose={() => setBenchmarkOpen(false)}
          />
        )}
      </>
    );
  }

  // Fallback - send back to screensaver if state got inconsistent.
  return <Screensaver onEnter={() => setScreen("society")} />;
}

export default App;
