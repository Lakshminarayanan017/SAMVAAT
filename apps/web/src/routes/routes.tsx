/**
 * The route table (Blueprint §5.3).
 *
 * Declared as data rather than as JSX scattered through a component, for two
 * reasons that both matter more than tidiness:
 *
 *   1. `tests/routes/contract.test.tsx` iterates this array and renders every
 *      route, asserting each one honours the accessible route contract. A route
 *      that exists only inside a `<Routes>` block cannot be enumerated, so the
 *      test could not see a route somebody forgot to wrap.
 *
 *   2. Code splitting is per entry. Each `load` is a dynamic import, so a
 *      learner who never opens the trainer dashboard never downloads it — and
 *      our learners are explicitly on entry-level Android and metered data.
 *
 * `chromeless` marks the four full-screen surfaces. A learner mid-mission
 * should see the mission and nothing else.
 */
import { lazy, type ComponentType } from 'react';

export interface RouteSpec {
  path: string;
  /** Shown in the tab title, announced on arrival, names `<main>`. */
  title: string;
  /** Full-screen, no navigation chrome. */
  chromeless?: boolean;
  /** Which roles may see it. Absent means every signed-in learner. */
  role?: 'trainer' | 'institution';
  /** Hidden from the navigation but still routable. */
  hidden?: boolean;
  /** Label in the navigation. Absent for hidden routes. */
  navLabel?: string;
  component: ComponentType<Record<string, never>>;
}

/**
 * Every route is lazily loaded, including the home screen.
 *
 * Lazy-loading home looks pointless — it is always needed — but it keeps the
 * initial bundle to the shell alone, so the app renders its skeleton and its
 * offline banner before any feature code arrives. On a slow connection that is
 * the difference between a blank page and a page that says what is happening.
 */
const Home = lazy(() => import('@/routes/screens/HomeScreen'));
const WorldScreen = lazy(() => import('@/routes/screens/WorldScreen'));
const LevelScreen = lazy(() => import('@/routes/screens/LevelScreen'));
const InterviewScreen = lazy(() => import('@/routes/screens/InterviewScreen'));
const StoriesScreen = lazy(() => import('@/routes/screens/StoriesScreen'));
const ProgressScreen = lazy(() => import('@/routes/screens/ProgressScreen'));
const DataScreen = lazy(() => import('@/routes/screens/DataScreen'));
const SettingsScreen = lazy(() => import('@/routes/screens/SettingsScreen'));
const TrainerScreen = lazy(() => import('@/routes/screens/TrainerScreen'));
const InstitutionScreen = lazy(() => import('@/routes/screens/InstitutionScreen'));
const DemoScreen = lazy(() => import('@/routes/screens/DemoScreen'));

export const ROUTES: RouteSpec[] = [
  { path: '/', title: 'Home', navLabel: 'Home', component: Home },
  { path: '/world/:worldId', title: 'World', hidden: true, component: WorldScreen },

  // The four full-screen surfaces.
  { path: '/level/:levelId', title: 'Level', chromeless: true, hidden: true, component: LevelScreen },
  {
    path: '/interview',
    title: 'Practise an interview',
    navLabel: 'Practise an interview',
    chromeless: true,
    component: InterviewScreen,
  },

  {
    path: '/stories',
    title: 'Understand a situation',
    navLabel: 'Understand a situation',
    component: StoriesScreen,
  },
  { path: '/me', title: 'My progress', navLabel: 'My progress', component: ProgressScreen },
  { path: '/me/data', title: 'Your data', navLabel: 'Your data', component: DataScreen },
  {
    path: '/me/settings',
    title: 'How this app talks to me',
    navLabel: 'Settings',
    component: SettingsScreen,
  },

  {
    path: '/trainer',
    title: 'My learners',
    navLabel: 'My learners',
    role: 'trainer',
    component: TrainerScreen,
  },
  {
    path: '/institution',
    title: 'Cohort report',
    navLabel: 'Cohort report',
    role: 'institution',
    component: InstitutionScreen,
  },

  // Moved out of the learner navigation (Blueprint A8). It is a superb pitch
  // artefact — one block rendered through five channels — and not a thing a
  // learner needs in their nav.
  { path: '/demo', title: 'How this works', hidden: true, component: DemoScreen },
];

/** Routes a learner in this role should see in the navigation. */
export function navigationFor(options: {
  isTrainer: boolean;
  isInstitution: boolean;
}): RouteSpec[] {
  return ROUTES.filter((route) => {
    if (route.hidden || !route.navLabel) return false;
    if (route.role === 'trainer') return options.isTrainer;
    if (route.role === 'institution') return options.isInstitution;
    return true;
  });
}
