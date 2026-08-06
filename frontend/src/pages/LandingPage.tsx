import { ArrowRight, Heart, Sparkles } from "lucide-react";
import seoulForestImage from "../assets/namsan-background.svg";
import chatbotImage from "../assets/wedding-chatbot.svg";
import newlywedsImage from "../assets/wedding-couple.svg";
import { categories } from "../data/policies";

type LandingPageProps = {
  onStart: () => void;
  isLeaving: boolean;
};

export function LandingPage({ onStart, isLeaving }: LandingPageProps) {
  return (
    <main className={`min-h-screen bg-brand-background text-text-primary transition-opacity duration-200 ${isLeaving ? "opacity-0" : "opacity-100"}`}>
      <section className="mx-auto grid min-h-[680px] w-full max-w-[1440px] grid-cols-1 items-center gap-10 px-6 py-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(520px,1.1fr)] lg:px-16">
        <div className="max-w-[600px]">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-brand-surface px-4 py-2 text-caption text-text-secondary">
            <Sparkles size={16} className="text-brand-primary" />
            서울 예비·신혼부부 정책 내비게이터
          </div>
          <h1 className="text-[42px] font-extrabold leading-[54px] tracking-[-0.02em] md:text-h1">
            나만 결혼 혜택?!
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
          <div className="mt-10 flex flex-col gap-4 sm:flex-row">
            <button
              type="button"
              onClick={onStart}
              className="inline-flex h-14 items-center justify-center gap-3 rounded-xl bg-brand-primary px-7 text-body-md text-white shadow-cta transition duration-200 hover:-translate-y-0.5 hover:brightness-90 active:scale-95"
            >
              챗봇으로 시작하기
              <ArrowRight size={20} />
            </button>
            <a
              href="#support"
              className="inline-flex h-14 items-center justify-center rounded-xl border border-brand-border px-7 text-body-md text-text-primary transition duration-200 hover:bg-brand-surface"
            >
              주요 지원 분야 보기
            </a>
          </div>
        </div>

        <div className="relative min-h-[560px] overflow-hidden rounded-3xl bg-brand-surface shadow-card">
          <img src={seoulForestImage} alt="서울 숲 배경" className="absolute inset-x-0 bottom-0 h-[52%] w-full object-cover" />
          <img src={newlywedsImage} alt="신혼부부 일러스트" className="absolute bottom-8 right-6 z-10 w-[58%] max-w-[520px] rounded-3xl shadow-card" />
          <img src={chatbotImage} alt="챗봇 캐릭터" className="absolute left-8 top-8 z-10 w-[34%] max-w-[260px] rounded-3xl shadow-card" />
          <div className="absolute left-8 bottom-8 z-20 max-w-[320px] rounded-3xl bg-white/90 p-6 shadow-card backdrop-blur">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-brand-surface-container text-brand-primary">
              <Heart size={24} fill="currentColor" />
            </div>
            <h2 className="text-h4">우리 조건을 묻고, 정책 근거를 남겨요</h2>
            <p className="mt-2 text-body-sm text-text-secondary">혼인 상태, 서울 거주, 소득, 주택 보유 여부를 차례로 확인합니다.</p>
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
