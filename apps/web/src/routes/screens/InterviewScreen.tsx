/**
 * Route screen: Practise an interview.
 *
 * Chromeless (Blueprint §5.3). A learner mid-interview should see the interview
 * and nothing else — navigation that stays on screen during a task is
 * navigation inviting them to leave it.
 */
import { InterviewSession } from '@/features/interview/InterviewSession';
import { AppRoute } from '@/routes/AppRoute';
import { useSession } from '@/services/SessionProvider';

export default function InterviewScreen() {
  const { session } = useSession();
  return (
    <AppRoute title="Practise an interview" chromeless>
      <InterviewSession userId={session.userId} />
    </AppRoute>
  );
}
