from so101_monitoring.logging_config import configure_logging
from so101_monitoring.state_machine import Machine, Event


def main():
    configure_logging()

    m = Machine()
    m.dispatch(Event.GRASP_PLAN_SUCCESS)


if __name__ == "__main__":
    main()
