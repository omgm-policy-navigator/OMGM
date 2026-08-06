import { QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ChatbotPage } from "@/pages/ChatbotPage";
import { LandingPage } from "@/pages/LandingPage";
import { queryClient } from "./providers/queryClient";

type Route = "/" | "/chatbot";

function getRoute(): Route {
  return window.location.pathname === "/chatbot" ? "/chatbot" : "/";
}

export function App() {
  const [route, setRoute] = useState<Route>(getRoute);
  const [isLeavingLanding, setIsLeavingLanding] = useState(false);

  useEffect(() => {
    const handlePopState = () => {
      const nextRoute = getRoute();
      setRoute(nextRoute);
      if (nextRoute === "/") {
        setIsLeavingLanding(false);
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = (nextRoute: Route, hash?: string) => {
    window.history.pushState({}, "", `${nextRoute}${hash ? `#${hash}` : ""}`);
    setRoute(nextRoute);
    if (nextRoute === "/") {
      setIsLeavingLanding(false);
    }

    if (hash) {
      window.requestAnimationFrame(() => {
        const target = document.getElementById(hash);
        if (typeof target?.scrollIntoView === "function") {
          target.scrollIntoView({ block: "start" });
        }
      });
    }
  };

  const startChat = () => {
    setIsLeavingLanding(true);
    window.setTimeout(() => navigate("/chatbot", "chat"), 200);
  };

  return (
    <QueryClientProvider client={queryClient}>
      {route === "/chatbot" ? (
        <ChatbotPage currentPath={route} onNavigate={navigate} />
      ) : (
        <LandingPage onStart={startChat} isLeaving={isLeavingLanding} />
      )}
    </QueryClientProvider>
  );
}
