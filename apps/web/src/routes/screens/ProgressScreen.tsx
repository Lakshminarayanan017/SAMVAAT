/**
 * Route screen: My progress.
 */
import { ProgressPanel } from '@/features/progress/ProgressPanel';
import { AppRoute } from '@/routes/AppRoute';
import { useSession } from '@/services/SessionProvider';

export default function ProgressScreen() {
  const { session } = useSession();
  return (
    <AppRoute title="My progress">
      <ProgressPanel token={session.token} />
    </AppRoute>
  );
}
