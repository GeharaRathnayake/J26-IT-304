# AI-Based Adaptive Java Learning Platform

A four-component AI-based adaptive Java learning platform for a final-year university research project.


Student Dashboard UI Template

The initial UI template for the Student Dashboard has been created with a modular, scalable file structure matching your reference design.

📁 Project Architecture & File Structure
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── main.tsx
    ├── index.css                     # Design system variables & styling tokens
    ├── app/
    │   ├── App.tsx                   # Root React App component
    │   └── Router.tsx                # Client-side routing for all components
    ├── components/
    │   ├── common/                   # Reusable UI primitives
    │   │   ├── Badge.tsx             # Badges (VAPI status, WEAK alerts)
    │   │   ├── Breadcrumbs.tsx       # Breadcrumb navigation trail
    │   │   ├── Button.tsx            # Action buttons
    │   │   ├── Card.tsx              # Rounded card containers with elevation
    │   │   └── ProgressBar.tsx       # Progress visualizers for strategies
    │   └── dashboard/                # Student Dashboard widgets
    │       ├── HeroBanner.tsx        # "Welcome, Demo" & Voice Tutor CTA
    │       ├── MetricCards.tsx       # 4 Metric cards (Level, Concepts, Weak topics, Style)
    │       ├── WeaknessTopicCard.tsx # Weakness Topic Area list
    │       └── StrategyEffectivenessCard.tsx # Theory, Example, Simplified, Analogy stats
    ├── layouts/
    │   ├── MainLayout.tsx            # Viewport & page wrapper
    │   ├── Sidebar.tsx               # Navigation sidebar with 4 research components
    │   └── Header.tsx                # Breadcrumbs + VAPI status indicator
    ├── pages/
    │   ├── StudentDashboard.tsx      # Main Student Dashboard
    │   ├── JavaIDETutor.tsx          # 1st Component
    │   ├── JavaVoiceTutor.tsx        # 2nd Component
    │   ├── AdaptiveQuiz.tsx          # 3rd Component
    │   └── SmartVideoLearning.tsx    # 4th Component
    ├── services/
    │   └── dashboardService.ts       # Student analytics data service
    └── types/
        └── index.ts                  # Strong TypeScript definitions
✨ Features Implemented
Sidebar Navigation:

Java LMS brand header with cyan/teal icon.
5 integrated navigation routes:


Student Dashboard
 (Active)


Java IDE Tutor
 (1st component)


Java Voice Tutor
 (2nd component)


Adaptive Quiz
 (3rd component)


Smart Video Learning
 (4th component)

🚀 Running the Frontend
The dev server is currently running at:

http://localhost:3000


🛠️ Tech Stack Summary:
Framework: React 18 (react, react-dom)
Language: TypeScript for strong typing across components and data models (

src/types/index.ts
)
Build Tool & Bundler: Vite for instant HMR and fast builds (

vite.config.ts
)
Routing: react-router-dom (v6) for seamless client-side page transitions (

src/app/Router.tsx
)
Icons: lucide-react for modern, lightweight icons
Styling: Vanilla CSS with modular CSS files and CSS variables (

src/index.css
) for custom design fidelity without heavy external CSS framework overhead.

