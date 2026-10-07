data("AirPassengers")

decomp <- decompose(AirPassengers, type = "multiplicative")

autoplot(decomp) + ggtitle("Декомпозицияи временного ряда") + theme_minimal()

train_set <- subset(AirPassengers, end = length(AirPassengers) - 12)
test_set <- subset(AirPassengers, start = length(AirPassengers) - 11)

cat("Длина обучающей выборки:", length(train_set), "\n")
cat("Длина тестовой выборки:", length(test_set), "\n")

fit_ets <- ets(train_set)
summary(fit_ets)

fit_arima <- auto.arima(train_set, seasonal = TRUE)
summary(fit_arima)

fc_ets <- forecast(fit_ets, h = 12)
fc_arima <- forecast(fit_arima, h = 12)

autoplot(train_set) +
  autolayer(fc_ets, series = "ETS", PI = FALSE) +
  autolayer(fc_arima, series = "ARIMA", PI = FALSE) +
  autolayer(test_set, series = "Реальные данные") +
  ggtitle("Сравнение прогнозов ETS и ARIMA на тестовой выборке") +
  theme_minimal()

smape_calc <- function(actual, forecast) {
  mean(2 * abs(actual - forecast) / (abs(actual) + abs(forecast))) * 100
}

mae_ets <- accuracy(fc_ets, test_set)["Test set", "MAE"]
smape_ets <- smape_calc(test_set, fc_ets$mean)

mae_arima <- accuracy(fc_arima, test_set)["Test set", "MAE"]
smape_arima <- smape_calc(test_set, fc_arima$mean)

results <- data.frame(
  Model = c("ETS", "ARIMA"),
  MAE = c(mae_ets, mae_arima),
  sMAPE_percent = c(smape_ets, smape_arima)
)

print(results)

final_fit <- auto.arima(AirPassengers, seasonal = TRUE)

final_forecast <- forecast(final_fit, h = 24)

autoplot(final_forecast) +
  ggtitle("Прогноз на 24 месяца с использованием ARIMA") +
  ylab("Количество пассажиров") +
  xlab("Год") +
  theme_minimal()










