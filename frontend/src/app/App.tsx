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
    const handlePopState = () => setRoute(getRoute());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = (nextRoute: Route) => {
    window.history.pushState({}, "", nextRoute);
    setRoute(nextRoute);
  };

  const startChat = () => {
    setIsLeavingLanding(true);
    window.setTimeout(() => navigate("/chatbot"), 200);
  };

  return (
    <QueryClientProvider client={queryClient}>
      {route === "/chatbot" ? <ChatbotPage /> : <LandingPage onStart={startChat} isLeaving={isLeavingLanding} />}
    </QueryClientProvider>
  );
}
