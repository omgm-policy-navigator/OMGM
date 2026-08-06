import type { LucideIcon } from "lucide-react";
import { Baby, Banknote, CalendarDays, HandHeart, Home, Landmark, ReceiptText, ShieldCheck } from "lucide-react";

export type PolicyCategory = {
  id: string;
  label: string;
  description: string;
  backendCategoryCode: string;
  liveNote?: string;
  icon: LucideIcon;
};

export type PolicyNodeData = {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
  status: "eligible" | "checking" | "recommended";
};

export const categories: PolicyCategory[] = [
  { id: "housing", label: "주거", description: "전월세, 임차보증금, 공공임대", backendCategoryCode: "housing", icon: Home },
  { id: "loan", label: "대출", description: "이자지원, 신혼부부 전용 대출", backendCategoryCode: "loan", icon: Banknote },
  {
    id: "wedding",
    label: "웨딩",
    description: "공공 예식장, 결혼 준비 지원",
    backendCategoryCode: "cash",
    liveNote: "백엔드 질문 엔진에 웨딩 전용 category가 없어 현금성 지원 흐름으로 임시 연결합니다.",
    icon: HandHeart,
  },
  {
    id: "tax",
    label: "세제 혜택",
    description: "공제, 감면, 신고 일정",
    backendCategoryCode: "education",
    liveNote: "백엔드 질문 엔진에 세제 전용 category가 없어 재무 상담/교육 흐름으로 임시 연결합니다.",
    icon: ReceiptText,
  },
  { id: "childcare", label: "출산/육아", description: "출산가구, 보육, 돌봄 지원", backendCategoryCode: "childcare", icon: Baby },
];

export const policyNodes: PolicyNodeData[] = [
  {
    id: "housing-cost",
    label: "신혼부부 주거비 지원",
    description: "서울 거주 및 무주택 조건을 기준으로 월세/주거비 지원 가능성을 확인합니다.",
    icon: Home,
    status: "recommended",
  },
  {
    id: "deposit-loan",
    label: "임차보증금 이자지원",
    description: "부부 합산 소득과 임대차 계약 조건을 바탕으로 이자지원 대상 여부를 안내합니다.",
    icon: Landmark,
    status: "eligible",
  },
  {
    id: "public-wedding",
    label: "서울시 공공 예식장",
    description: "예비부부가 이용 가능한 공공기관 예식장 예약 일정과 필요 서류를 확인합니다.",
    icon: CalendarDays,
    status: "checking",
  },
  {
    id: "tax-benefit",
    label: "혼인 세제 혜택",
    description: "혼인신고 및 세대 구성에 따른 공제·감면 항목을 정리합니다.",
    icon: ReceiptText,
    status: "checking",
  },
  {
    id: "birth-family",
    label: "출산가구 주거 지원",
    description: "출산 예정 또는 자녀 계획이 있는 가구의 후속 지원 정책을 연결합니다.",
    icon: Baby,
    status: "eligible",
  },
  {
    id: "evidence",
    label: "자격 근거 확인",
    description: "최종 자격 판정 전에 혼인상태, 거주지, 소득, 주택 보유 여부를 구조화해 확인합니다.",
    icon: ShieldCheck,
    status: "recommended",
  },
];
