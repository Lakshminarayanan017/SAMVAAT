/**
 * Route screen: Your data — export and erasure.
 */
import { YourData } from '@/features/privacy/YourData';
import { AppRoute } from '@/routes/AppRoute';
import { useSession } from '@/services/SessionProvider';

export default function DataScreen() {
  const { session } = useSession();
  return (
    <AppRoute title="Your data">
      <YourData token={session.token} />
    </AppRoute>
  );
}
