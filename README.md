# OpenInsider 모니터링 시스템

실시간 내부자 거래 추적 및 AI 종목 추천 시스템

## 🚀 무료 배포 방법

### 1. Netlify (추천)
```bash
# Netlify Drop 사용
1. https://app.netlify.com/drop 접속
2. openinsider-monitor 폴더를 드래그 앤 드롭
3. 자동으로 배포 완료
```

### 2. Vercel
```bash
# GitHub 연동 후 배포
1. GitHub에 리포지토리 생성
2. https://vercel.com 접속
3. "New Project" → GitHub 리포지토리 선택
4. 자동 배포 완료
```

### 3. GitHub Pages
```bash
# GitHub Pages 설정
1. GitHub 리포지토리 생성
2. Settings → Pages
3. Source: Deploy from a branch → main
4. https://username.github.io/openinsider-monitor 접속
```

### 4. Firebase Hosting
```bash
# Firebase CLI 설치 및 배포
npm install -g firebase-tools
firebase login
firebase init hosting
firebase deploy
```

## ✨ 주요 기능

- 📊 실시간 내부자 거래 모니터링
- 🔔 브라우저 알림 시스템
- 🧠 AI 기반 종목 추천
- 💾 로컬 데이터 저장
- 📱 반응형 웹 디자인

## 🎯 사용법

1. 브라우저에서 index.html 실행
2. 알림 권한 허용
3. 매일 오전 9시 자동 체크
4. "지금 체크하기"로 수동 체크 가능

## 📁 프로젝트 구조

```
openinsider-monitor/
├── index.html          # 메인 애플리케이션
├── README.md           # 프로젝트 설명서
└── package.json        # 배포 설정
```

## 🔧 기술 스택

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Storage**: localStorage
- **Deployment**: 정적 파일 호스팅 서비스

## 📋 모니터링 종목

- TSLA (Tesla)
- PLTR (Palantir)
- RGTI (Rigetti Computing)
- IONQ (IonQ)
- MSTR (MicroStrategy)
- LLY (Eli Lilly)

## 🏆 AI 추천 시스템

S&P 500 종목을 대상으로 4가지 요소를 분석:
- 거래금액 (40% 가중치)
- 발행주식 비율 (30% 가중치)
- 임원 직급 (20% 가중치)
- 집중도 (10% 가중치)

## 🚨 알림 조건

3개월 내 BUY 또는 SELL 이벤트가 3건 이상 발생시 자동 알림

## ⚠️ 주의사항

- 이 시스템은 참고용으로만 사용하세요
- 투자 결정은 반드시 추가 분석 후 내리시기 바랍니다
- 시뮬레이션 데이터를 사용하므로 실제 배포시 API 연동이 필요합니다

## 📞 지원

문제가 발생하면 GitHub Issues를 통해 문의해주세요.