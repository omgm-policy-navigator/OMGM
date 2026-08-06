import { useEffect, useState } from "react";
import { ChatbotPage } from "./pages/ChatbotPage";
import { LandingPage } from "./pages/LandingPage";

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

  if (route === "/chatbot") {
    return <ChatbotPage />;
  }

  return <LandingPage onStart={startChat} isLeaving={isLeavingLanding} />;
}
