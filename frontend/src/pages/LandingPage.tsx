import { ArrowRight, Sparkles } from "lucide-react";
import type { CSSProperties, PointerEvent } from "react";
import seoulForestImage from "../assets/namsan-background.svg";
import chatbotImage from "../assets/wedding-chatbot.svg";
import newlywedsImage from "../assets/wedding-couple.svg";
import { categories } from "../data/policies";

type LandingPageProps = {
  onStart: () => void;
  isLeaving: boolean;
};

export function LandingPage({ onStart, isLeaving }: LandingPageProps) {
  const handleHeroPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty("--hero-spot-x", `${event.clientX - bounds.left}px`);
    event.currentTarget.style.setProperty("--hero-spot-y", `${event.clientY - bounds.top}px`);
    event.currentTarget.style.setProperty("--hero-spot-opacity", "1");
    event.currentTarget.style.setProperty("--hero-mood-opacity", "1");
  };

  const handleHeroPointerLeave = (event: PointerEvent<HTMLDivElement>) => {
    event.currentTarget.style.setProperty("--hero-spot-opacity", "0");
    event.currentTarget.style.setProperty("--hero-mood-opacity", "0");
  };

  return (
    <main className={`min-h-screen bg-brand-background text-text-primary transition-opacity duration-200 ${isLeaving ? "opacity-0" : "opacity-100"}`}>
      <section className="mx-auto flex min-h-[680px] w-full max-w-[1440px] items-center px-6 py-10 lg:px-16">
        <div
          className="hero-consultation-card relative min-h-[560px] w-full overflow-hidden rounded-3xl bg-[#f0eeee] shadow-card"
          onPointerMove={handleHeroPointerMove}
          onPointerLeave={handleHeroPointerLeave}
          style={{ "--hero-spot-x": "50%", "--hero-spot-y": "50%", "--hero-spot-opacity": "0", "--hero-mood-opacity": "0" } as CSSProperties}
        >
          <div className="hero-consultation-card__mood" aria-hidden="true" />
          <div className="hero-consultation-card__spotlight" aria-hidden="true" />
          <img src={seoulForestImage} alt="" className="absolute inset-x-0 bottom-0 h-[44%] w-full object-cover opacity-45" />
          <div className="landing-chatbot-figure absolute bottom-[-3%] left-[-6%] z-10 hidden h-[100%] max-h-[640px] w-[46%] transition duration-200 hover:-translate-y-2 lg:block">
            <div className="absolute left-[53%] top-[57%] h-[82%] w-[88%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(250,220,214,0.78)_0%,rgba(250,220,214,0.42)_44%,rgba(250,220,214,0)_74%)] blur-sm" />
            <img src={chatbotImage} alt="챗봇 캐릭터" className="relative z-10 h-full w-full object-contain object-bottom" />
          </div>
          <img
            src={newlywedsImage}
            alt="신혼부부 일러스트"
            className="absolute bottom-0 right-[-8%] z-10 h-[68%] max-h-[430px] w-[50%] object-contain object-bottom transition duration-200 hover:-translate-y-2 md:right-[-4%]"
          />
          <div className="relative z-20 mx-auto flex max-w-[560px] flex-col items-center px-8 py-12 text-center md:px-16 md:py-20">
            <div className="mb-7 inline-flex w-fit items-center justify-center gap-2 rounded-full bg-white/80 px-4 py-2 text-caption text-text-secondary shadow-sm backdrop-blur">
              <Sparkles size={16} className="text-brand-primary" />
              서울 예비·신혼부부 정책 내비게이터
            </div>
            <h1 className="text-[48px] font-extrabold leading-[60px] tracking-[-0.02em] text-[#243927] md:text-[56px] md:leading-[68px]">
              나만 결혼해?!
              <br />
              <span className="mt-3 inline-block text-[28px] font-bold leading-10 tracking-[-0.01em] text-text-primary md:text-h2">
                결혼 준비부터 신혼 생활까지
                <br />
                <span className="text-brand-primary">정책을 한눈에.</span>
              </span>
            </h1>
            <p className="mt-6 max-w-[520px] text-body-lg text-text-secondary">
              주거, 대출, 웨딩, 세제 혜택, 출산/육아 정책을 대화로 확인하고 우리 부부에게 연결되는 정책 그래프를 바로 탐색하세요.
            </p>
            <div className="mt-10 flex w-full flex-col items-center justify-center gap-4 sm:flex-row">
              <button
                type="button"
                onClick={onStart}
                className="inline-flex h-14 min-w-[190px] items-center justify-center gap-3 whitespace-nowrap rounded-xl bg-brand-primary px-7 text-body-md text-white shadow-cta transition duration-200 hover:-translate-y-0.5 hover:brightness-90 active:scale-95"
              >
                챗봇으로 시작하기
                <ArrowRight size={20} className="shrink-0" />
              </button>
              <a
                href="#support"
                className="inline-flex h-14 min-w-[190px] items-center justify-center whitespace-nowrap rounded-xl border border-brand-border bg-white/70 px-7 text-body-md text-text-primary transition duration-200 hover:bg-brand-surface"
              >
                주요 지원 분야 보기
              </a>
            </div>
          </div>
        </div>
      </section>

      <section id="support" className="mx-auto w-full max-w-[1440px] px-6 pb-20 lg:px-16">
        <div className="mb-8 flex items-end justify-between gap-6">
          <div>
            <p className="text-caption text-brand-primary">Support Categories</p>
            <h2 className="mt-2 text-h2">주요 지원 분야</h2>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {categories.map(({ id, label, description, icon: Icon }) => (
            <article key={id} className="rounded-xl border border-brand-border bg-white p-6 shadow-card transition duration-200 hover:-translate-y-1 hover:bg-brand-surface">
              <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-xl bg-brand-surface-container text-brand-primary">
                <Icon size={26} />
              </div>
              <h3 className="text-h4">{label}</h3>
              <p className="mt-2 text-body-sm text-text-secondary">{description}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
