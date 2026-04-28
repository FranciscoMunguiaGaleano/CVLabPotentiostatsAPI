"""FastAPI server for controlling multiple potentiostat devices.

This server provides REST API endpoints for performing various electrochemical
measurements including cyclic voltammetry, linear voltammetry, open circuit
measurements, and electrolysis experiments.
"""

from potentiostat import Potentiostat, I_range_mode
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from decimal import Decimal
import logging


potentiostats: list[Potentiostat] = []

POTENTIOSTAT_PORTS = ["/dev/ttypotentiostat_3", "/dev/ttypotentiostat_2", "/dev/ttypotentiostat_1"]


async def lifespan(app: FastAPI):
    """Manage the lifespan of the FastAPI application.

    Initializes potentiostat devices on startup and safely shuts them down
    on application termination.

    Args:
    
    
    
        app: The FastAPI application instance

    Yields:
        Control back to the application during runtime
    """
    loggers = []
    for i in range(1, 4):
        p_logger = logging.getLogger(f"Potentiostat_{i}")
        logging.basicConfig(
            filename="CV_lab_potentiostats.log",
            encoding="utf-8",
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        loggers.append(p_logger)
        try:
            
            p = Potentiostat(POTENTIOSTAT_PORTS[i-1], f"P{i}_", logger=loggers[i-1])
        except Exception as e:
            logger.warning(f"Could not load potentiostat in port {POTENTIOSTAT_PORTS[i-1]}")
            logger.error(f"{e}")
            p = None
        potentiostats.append(p)
    yield
    for i in potentiostats:
        if i is not None:
            i._shutdown()


app = FastAPI(lifespan=lifespan)

logger = logging.getLogger("Fast_api_server")


@app.get("/")
async def root():
    """Root endpoint returning a welcome message.

    Returns:
        dict: Welcome message
    """
    logger.info("GET /")
    return {"message": "Hello World"}


@app.get("/{potentiostat_id}/status")
async def get_status(potentiostat_id: int):
    """Get the error status of a specific potentiostat.

    Args:
        potentiostat_id: ID of the potentiostat (1-indexed)

    Returns:
        str: Error status message
    """

    logger.info(f"GET /{potentiostat_id}/status")
    try:
        working_p = potentiostats[potentiostat_id - 1]
    except IndexError:
        logger.error(f"No potentiostat with id {potentiostat_id}")
        raise HTTPException(status_code=404,detail=f"No potentiostat with id {potentiostat_id}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=e)

    if working_p is None:
        logger.info(f"{potentiostat_id} is disabled or not connected")
        raise HTTPException(status_code=409,detail=f"Potentiostat: {potentiostat_id} is disabled or not connected")
    try:
        ret = "error: " + working_p.get_status()
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=e)
    logger.info(f"{ret}")
    return ret


@app.post("/{potentiostat_id}/cyclic_voltemmetry")
async def do_cyclic_voltemmetry(
    potentiostat_id: int,
    i_range: I_range_mode,
    start_potential: Decimal,
    potential_vertex: Decimal,
    scan_rate: float,
    cycles: int,
    increment=Decimal("0.01"),
):
    """Perform cyclic voltammetry measurement on a specific potentiostat.

    Executes a cyclic voltammetry experiment, sweeping potential between
    start_potential and potential_vertex for the specified number of cycles.

    Args:
        potentiostat_id: ID of the potentiostat to use (1-indexed)
        i_range: Current range setting for the measurement
        start_potential: Starting potential in volts
        potential_vertex: Maximum potential to reach before reversing in volts
        scan_rate: Rate of potential change in V/s
        cycles: Number of forward-reverse cycles to perform
        increment: Potential step size in volts (default: 0.01)

    Returns:
        FileResponse: CSV file containing voltage and current data
    """
    logger.info(f"POST /{potentiostat_id}/cyclic_voltemmetry")
    logger.info(
        f"Cyclic_voltemmetry with args {i_range},{start_potential},{potential_vertex},{scan_rate},{cycles},{increment}"
    )
    try:
        working_p = potentiostats[potentiostat_id - 1]
    except IndexError:
        logger.error(f"No potentiostat with id {potentiostat_id}")
        raise HTTPException(status_code=404,detail=f"No potentiostat with id {potentiostat_id}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=e)

    if working_p is None:
        logger.info(f"{potentiostat_id} is disabled or not connected")
        raise HTTPException(status_code=409,detail=f"Potentiostat: {potentiostat_id} is disabled or not connected")
    
    ret = working_p.cyclic_voltemmetry(
        i_range=i_range,
        start_potential=Decimal(start_potential),
        potential_vertex=Decimal(potential_vertex),
        scan_rate=scan_rate,
        cycles=cycles,
        increment=Decimal(increment),
    )
    logger.info(f"Reponse stored in {ret}")
    return FileResponse(ret)


@app.post("/{potentiostat_id}/linear_voltemmetry")
async def do_linear_voltemmetry(
    potentiostat_id: int,
    i_range: I_range_mode,
    start_potential: Decimal,
    end_potential: Decimal,
    scan_rate: float,
    increment=Decimal("0.01"),
):
    """Perform linear sweep voltammetry measurement on a specific potentiostat.

    Executes a linear voltammetry experiment, sweeping potential linearly
    from start_potential to end_potential.

    Args:
        potentiostat_id: ID of the potentiostat to use (1-indexed)
        i_range: Current range setting for the measurement
        start_potential: Starting potential in volts
        end_potential: Final potential in volts
        scan_rate: Rate of potential change in V/s
        increment: Potential step size in volts (default: 0.01)

    Returns:
        FileResponse: CSV file containing voltage and current data
    """
    logger.info(f"POST /{potentiostat_id}/linear_voltemmetry")
    logger.info(
        f"Linear_voltemmetry with args {i_range},{start_potential},{end_potential},{scan_rate},{increment}"
    )
    
    try:
        working_p = potentiostats[potentiostat_id - 1]
    except IndexError:
        logger.error(f"No potentiostat with id {potentiostat_id}")
        raise HTTPException(status_code=404,detail=f"No potentiostat with id {potentiostat_id}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=e)

    if working_p is None:
        logger.info(f"{potentiostat_id} is disabled or not connected")
        raise HTTPException(status_code=409,detail=f"Potentiostat: {potentiostat_id} is disabled or not connected")
    
    ret = working_p.linear_voltemmetry(
        i_range=i_range,
        start_potential=Decimal(start_potential),
        end_potential=Decimal(end_potential),
        scan_rate=scan_rate,
        increment=Decimal(increment),
    )
    logger.info(f"Reponse stored in {ret}")
    return FileResponse(ret)


@app.post("/{potentiostat_id}/open_circuit")
async def do_open_circuit(
    potentiostat_id: int,
    duration: float,
    sampling_period: float,
):
    """Measure open circuit potential over time on a specific potentiostat.

    Records the voltage without applying current, measuring the natural
    potential of the electrochemical system.

    Args:
        potentiostat_id: ID of the potentiostat to use (1-indexed)
        duration: Total measurement time in seconds
        sampling_period: Time between measurements in seconds

    Returns:
        FileResponse: CSV file containing time and voltage data
    """
    logger.info(f"POST /{potentiostat_id}/open_circuit")
    logger.info(f"Open_circuit with args {duration},{sampling_period}")
    try:
        working_p = potentiostats[potentiostat_id - 1]
    except IndexError:
        logger.error(f"No potentiostat with id {potentiostat_id}")
        raise HTTPException(status_code=404,detail=f"No potentiostat with id {potentiostat_id}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=e)

    if working_p is None:
        logger.info(f"{potentiostat_id} is disabled or not connected")
        raise HTTPException(status_code=409,detail=f"Potentiostat: {potentiostat_id} is disabled or not connected")
    ret = working_p.open_circuit(
        duration=duration,
        sampling_period=sampling_period,
    )
    logger.info(f"Reponse stored in {ret}")
    return FileResponse(ret)


@app.post("/{potentiostat_id}/electrolysis")
async def do_electrolysis(
    potentiostat_id: int,
    i_range: I_range_mode,
    potential: Decimal,
    duration: float,
    sampling_period: float,
):
    """Perform constant potential electrolysis on a specific potentiostat.

    Applies a constant potential and measures current over time.

    Args:
        potentiostat_id: ID of the potentiostat to use (1-indexed)
        i_range: Current range setting for the measurement
        potential: Constant potential to apply in volts
        duration: Total measurement time in seconds
        sampling_period: Time between current measurements in seconds

    Returns:
        FileResponse: CSV file containing time and current data
    """
    logger.info(f"POST /{potentiostat_id}/electrolysis")
    logger.info(
        f"Electrolysis with args {i_range},{potential},{duration},{sampling_period}"
    )
    try:
        working_p = potentiostats[potentiostat_id - 1]
    except IndexError:
        logger.error(f"No potentiostat with id {potentiostat_id}")
        raise HTTPException(status_code=404,detail=f"No potentiostat with id {potentiostat_id}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=e)

    if working_p is None:
        logger.info(f"{potentiostat_id} is disabled or not connected")
        raise HTTPException(status_code=409,detail=f"Potentiostat: {potentiostat_id} is disabled or not connected")
    
    ret = working_p.electrolysis(
        i_range=i_range,
        potential=Decimal(potential),
        duration=duration,
        sampling_period=sampling_period,
    )
    logger.info(f"Reponse stored in {ret}")
    return FileResponse(ret)


if __name__ == "__main__":
    import uvicorn
    # uvicorn potentiostat_server:app --host="0.0.0.0" --port=8000 --workers=5
    uvicorn.run(app, host="0.0.0.0", port=8000,workers=5)
