package availabilitycache_test

import (
	"context"
	"errors"
	"fmt"
	"reflect"
	"regexp"
	"strconv"
	"testing"
	"time"

	"github.com/cucumber/godog"

	ac "availability-cache"
)

func TestFeatures(t *testing.T) {
	suite := godog.TestSuite{
		ScenarioInitializer: initializeScenario,
		Options: &godog.Options{
			Format:   "pretty",
			Paths:    []string{"features"},
			Strict:   true, // an undefined or misspelled step must fail the suite
			TestingT: t,
		},
	}
	if suite.Run() != 0 {
		t.Fatal("feature scenarios failed")
	}
}

var epoch = time.Date(2026, 1, 1, 12, 0, 0, 0, time.UTC)

// fakeHost is the airline: it holds seats per key and counts the questions asked.
type fakeHost struct {
	seats   map[ac.Key]int
	failing map[ac.Key]bool // keys the host cannot answer about
	calls   int
}

var errHostDown = errors.New("host cannot answer")

func (h *fakeHost) Seats(k ac.Key) (int, error) {
	h.calls++
	if h.failing[k] {
		return 0, errHostDown
	}
	return h.seats[k], nil
}

func (h *fakeHost) setSeats(k ac.Key, seats int) {
	h.seats[k] = seats
	delete(h.failing, k)
}

// world is the state of one scenario.
type world struct {
	now       time.Time
	host      *fakeHost
	cache     *ac.Cache
	board     *ac.StatusBoard
	answer    int
	answerErr error
	cached    int
	cachedKey ac.Key // the key the cache said seats for
	checked   ac.Key // the last class whose status a scenario looked at
	offers    []ac.Key
	shown     []ac.Key
	caught    int
	messaged  []ac.Key // the classes the airline sent a status message for
}

func (w *world) clock() time.Time { return w.now }

func (w *world) advance(seconds int) {
	w.now = w.now.Add(time.Duration(seconds) * time.Second)
}

func (w *world) aCacheWithTTL(seconds int) {
	w.cache = ac.New(time.Duration(seconds)*time.Second, w.host, w.clock)
}

func (w *world) cacheHolds(seats int, class, flight string, ago int) {
	w.advance(-ago)
	w.cache.Update(ac.Key{Flight: flight, Class: class}, seats)
	w.advance(ago)
}

func (w *world) hostHas(seats int, class, flight string) {
	w.host.setSeats(ac.Key{Flight: flight, Class: class}, seats)
}

func (w *world) hostCannotAnswer(class, flight string) {
	w.host.failing[ac.Key{Flight: flight, Class: class}] = true
}

func (w *world) restricted(flight string) { w.cache.Restrict(flight) }

func (w *world) airlineSends(seats int, class, flight string) {
	w.cache.Update(ac.Key{Flight: flight, Class: class}, seats)
}

func (w *world) secondsPass(seconds int) { w.advance(seconds) }

func (w *world) clockGoesBack(seconds int) { w.advance(-seconds) }

func (w *world) requested(class, flight string) {
	w.answer, w.answerErr = w.cache.Availability(ac.Key{Flight: flight, Class: class})
}

func (w *world) requestFails() error {
	if w.answerErr == nil {
		return fmt.Errorf("the request answered %d seats, want a failure", w.answer)
	}
	return nil
}

func (w *world) answerIs(seats int) error {
	if w.answerErr != nil {
		return fmt.Errorf("the request failed: %v", w.answerErr)
	}
	if w.answer != seats {
		return fmt.Errorf("answer is %d seats, want %d", w.answer, seats)
	}
	return nil
}

func (w *world) hostAsked(times int) error {
	if w.host.calls != times {
		return fmt.Errorf("host was asked %d times, want %d", w.host.calls, times)
	}
	return nil
}

// cacheNowHolds reads the entry back without the host: the host answers 99 if asked,
// so a wrong value or a host call both fail. The host is left as it was.
func (w *world) cacheNowHolds(seats int, class, flight string) error {
	key := ac.Key{Flight: flight, Class: class}
	before, had := w.host.seats[key]
	callsBefore := w.host.calls
	w.host.seats[key] = 99
	got, _ := w.cache.Availability(key)
	asked := w.host.calls > callsBefore
	w.host.calls = callsBefore
	if had {
		w.host.seats[key] = before
	} else {
		delete(w.host.seats, key)
	}
	if asked {
		return fmt.Errorf("the cache holds no fresh entry for class %s on flight %s", class, flight)
	}
	if got != seats {
		return fmt.Errorf("cache holds %d seats, want %d", got, seats)
	}
	return nil
}

func (w *world) cacheSays(seats int, class, flight string) {
	w.cached = seats
	w.cachedKey = ac.Key{Flight: flight, Class: class}
}

func (w *world) resultIs(want string) error {
	got := ac.Classify(w.cached, w.host.seats[w.cachedKey])
	if got.String() != want {
		return fmt.Errorf("result is %q, want %q", got, want)
	}
	return nil
}

var flightPattern = regexp.MustCompile(`[A-Z]{2}\d+`)

func flights(list string) []string { return flightPattern.FindAllString(list, -1) }

func (w *world) cacheSaysOpenOn(class, list string) {
	for _, f := range flights(list) {
		w.offers = append(w.offers, ac.Key{Flight: f, Class: class})
	}
}

func (w *world) hostHasClosed(class, flight string) {
	w.host.setSeats(ac.Key{Flight: flight, Class: class}, 0)
}

func (w *world) topValidated(top int) {
	for _, k := range w.offers {
		if _, ok := w.host.seats[k]; !ok {
			w.host.seats[k] = 4
		}
	}
	w.shown, w.caught = ac.Wash(w.offers, top, w.host)
}

func (w *world) offersShown(list string) error {
	var want []ac.Key
	for _, f := range flights(list) {
		want = append(want, ac.Key{Flight: f, Class: "M"})
	}
	if !reflect.DeepEqual(w.shown, want) {
		return fmt.Errorf("offers shown %v, want %v", w.shown, want)
	}
	return nil
}

func (w *world) statusMessage(seats int, class, flight string) {
	key := ac.Key{Flight: flight, Class: class}
	w.board.Apply(key, seats)
	w.messaged = append(w.messaged, key)
}

// noMessageFor checks the scenario's premise: nothing was applied to the board for the class.
func (w *world) noMessageFor(class, flight string) error {
	key := ac.Key{Flight: flight, Class: class}
	for _, got := range w.messaged {
		if got == key {
			return fmt.Errorf("a status message was applied for class %s on flight %s", class, flight)
		}
	}
	return nil
}

func (w *world) classIs(class, flight, status string) error {
	w.checked = ac.Key{Flight: flight, Class: class}
	open := w.board.Open(w.checked)
	if open != (status == "open") {
		return fmt.Errorf("class %s on flight %s is open=%v, want %s", class, flight, open, status)
	}
	return nil
}

// comparedWithHost classifies the board's answer against the host. Only open or
// closed matters, so an open class counts as one seat.
func (w *world) comparedWithHost() error {
	key := w.checked
	if key == (ac.Key{}) {
		return fmt.Errorf("no class was looked at before comparing it with the host")
	}
	cached := 0
	if w.board.Open(key) {
		cached = 1
	}
	if got := ac.Classify(cached, w.host.seats[key]); got != ac.OpenWrong {
		return fmt.Errorf("comparison gives %q, want open-wrong", got)
	}
	return nil
}

func (w *world) errorsCaught(n int) error {
	if w.caught != n {
		return fmt.Errorf("%d open-wrong errors caught, want %d", w.caught, n)
	}
	return nil
}

func initializeScenario(sc *godog.ScenarioContext) {
	w := &world{} // method values below bind to this pointer; Before resets its contents
	sc.Before(func(ctx context.Context, _ *godog.Scenario) (context.Context, error) {
		*w = world{now: epoch, host: &fakeHost{seats: map[ac.Key]int{}, failing: map[ac.Key]bool{}}, board: ac.NewStatusBoard()}
		return ctx, nil
	})

	num := func(s string) int { n, _ := strconv.Atoi(s); return n }

	sc.Step(`^a cache with a time to live of (\d+) seconds$`, func(s string) { w.aCacheWithTTL(num(s)) })
	sc.Step(`^the cache holds (\d+) seats for class (\w+) on flight (\w+), stored (\d+) seconds ago$`,
		func(n, class, flight, ago string) { w.cacheHolds(num(n), class, flight, num(ago)) })
	sc.Step(`^the host has (\d+) seats for class (\w+) on flight (\w+)$`,
		func(n, class, flight string) { w.hostHas(num(n), class, flight) })
	sc.Step(`^the host cannot answer for class (\w+) on flight (\w+)$`, w.hostCannotAnswer)
	sc.Step(`^the clock goes back (\d+) seconds$`, func(s string) { w.clockGoesBack(num(s)) })
	sc.Step(`^the request fails$`, w.requestFails)
	sc.Step(`^flight (\w+) is market restricted$`, w.restricted)
	sc.Step(`^the airline sends an update of (\d+) seats for class (\w+) on flight (\w+)$`,
		func(n, class, flight string) { w.airlineSends(num(n), class, flight) })
	sc.Step(`^(\d+) seconds pass$`, func(s string) { w.secondsPass(num(s)) })
	sc.Step(`^availability for class (\w+) on flight (\w+) is requested$`, w.requested)
	sc.Step(`^the answer is (\d+) seats$`, func(s string) error { return w.answerIs(num(s)) })
	sc.Step(`^the host was asked (\d+) times?$`, func(s string) error { return w.hostAsked(num(s)) })
	sc.Step(`^the cache holds (\d+) seats for class (\w+) on flight (\w+)$`,
		func(n, class, flight string) error { return w.cacheNowHolds(num(n), class, flight) })

	sc.Step(`^the cache says (\d+) seats for class (\w+) on flight (\w+)$`,
		func(n, class, flight string) { w.cacheSays(num(n), class, flight) })
	sc.Step(`^the result is (.+)$`, w.resultIs)
	sc.Step(`^the cache says class (\w+) is open on flights (.+)$`, w.cacheSaysOpenOn)
	sc.Step(`^the host has class (\w+) closed on flight (\w+)$`, w.hostHasClosed)
	sc.Step(`^the top (\d+) offers are validated against the host$`, func(s string) { w.topValidated(num(s)) })
	sc.Step(`^the offers shown are on flights (.+)$`, w.offersShown)
	sc.Step(`^the airline (?:sends|sent) a status message of (\d+) seats for class (\w+) on flight (\w+)$`,
		func(n, class, flight string) { w.statusMessage(num(n), class, flight) })
	sc.Step(`^class (\w+) on flight (\w+) is (open|closed)$`, w.classIs)
	sc.Step(`^no status message was sent for class (\w+) on flight (\w+)$`, w.noMessageFor)
	sc.Step(`^the close message for class (\w+) on flight (\w+) never arrived$`, w.noMessageFor)
	sc.Step(`^comparing it with the host gives an open-wrong error$`, w.comparedWithHost)
	sc.Step(`^(\d+) open-wrong errors? (?:was|were) caught$`, func(s string) error { return w.errorsCaught(num(s)) })
}
