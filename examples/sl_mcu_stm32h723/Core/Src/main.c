/* USER CODE BEGIN Header */
/*----------------------------------------------------------------------------
 | @file           : main.c
 | @brief          : cmsynth on the STM32H723
 |----------------------------------------------------------------------------
 | @attention
 |
 | Copyright (c) 2026 CurrentMakers
 |
 | Released under the MIT License, see the LICENSE file in the root of
 | the cmsynth repository.
 |
 |----------------------------------------------------------------------------*/
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include "tusb.h"
#include "synth.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

// One synth block per half-buffer (64 frames = 1.33 ms)
#define I2S_DMA_BUFFER_SAMPLES SYNTH_BLOCK_SIZE

// Stereo (2 channels) * 2 half-buffers (Ping-Pong) * Samples
#define I2S_DMA_BUFFER_SIZE (2 * 2 * I2S_DMA_BUFFER_SAMPLES)

// Print cycles per sample for each synth stage at startup
#define SYNTH_BENCHMARK 1

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

I2S_HandleTypeDef hi2s2;
DMA_HandleTypeDef hdma_spi2_tx;

UART_HandleTypeDef huart1;

PCD_HandleTypeDef hpcd_USB_OTG_HS;

/* USER CODE BEGIN PV */

// In the AXI SRAM (DMA1 cannot reach the DTCM). The data cache is on, so each
// half is cleaned to RAM after rendering; 32 byte aligned for that.
int16_t i2s_dma_buffer[I2S_DMA_BUFFER_SIZE] __attribute__((aligned(32)));
volatile int16_t *dma_buffer_to_fill = NULL; // Deferred buffer processing pointer (volatile for ISR safety)

uint8_t change_wave = 0;

// Audio CPU load statistics (DWT cycle counter)
volatile uint32_t dma_overruns = 0;   // Half-buffers the main loop did not fill in time
uint32_t perf_cycles_sum = 0;
uint32_t perf_cycles_max = 0;
uint32_t perf_blocks = 0;

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MPU_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_I2S2_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_USB_OTG_HS_PCD_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

uint32_t dwt_cycles(void) {
    return DWT->CYCCNT;
}

/*
 * Non-blocking printf: characters go into a ring buffer that the USART1 TXE
 * interrupt empties, so debug output never stalls audio rendering. When the
 * buffer is full, characters are dropped rather than waiting.
 */
#define UART_TX_BUFFER_SIZE 2048

static volatile uint8_t uart_tx_buffer[UART_TX_BUFFER_SIZE];
static volatile uint16_t uart_tx_head = 0;
static volatile uint16_t uart_tx_tail = 0;

static void uart_put(uint8_t c) {
    uint16_t next = (uart_tx_head + 1) % UART_TX_BUFFER_SIZE;
    if (next == uart_tx_tail)
        return; // Full, drop
    uart_tx_buffer[uart_tx_head] = c;
    uart_tx_head = next;
    SET_BIT(USART1->CR1, USART_CR1_TXEIE_TXFNFIE);
}

// Called from USART1_IRQHandler (stm32h7xx_it.c)
void uart_tx_irq(void) {
    if ((USART1->ISR & USART_ISR_TXE_TXFNF) && (USART1->CR1 & USART_CR1_TXEIE_TXFNFIE)) {
        if (uart_tx_tail != uart_tx_head) {
            USART1->TDR = uart_tx_buffer[uart_tx_tail];
            uart_tx_tail = (uart_tx_tail + 1) % UART_TX_BUFFER_SIZE;
        } else {
            CLEAR_BIT(USART1->CR1, USART_CR1_TXEIE_TXFNFIE);
        }
    }
}

int __io_putchar(int ch) {
    if (ch == '\n')
        uart_put('\r');
    uart_put((uint8_t) ch);
    return ch;
}

/* Deferred ISR Callbacks Correctly dynamic for buffer size */
void HAL_I2S_TxHalfCpltCallback(I2S_HandleTypeDef *hi2s) {
    if (hi2s->Instance == SPI2) {
        if (dma_buffer_to_fill != NULL)
            ++dma_overruns;
        dma_buffer_to_fill = &i2s_dma_buffer[0];
    }
}

void HAL_I2S_TxCpltCallback(I2S_HandleTypeDef *hi2s) {
    if (hi2s->Instance == SPI2) {
        if (dma_buffer_to_fill != NULL)
            ++dma_overruns;
        dma_buffer_to_fill = &i2s_dma_buffer[I2S_DMA_BUFFER_SIZE / 2];
    }
}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin) {
    if (GPIO_Pin == BTN_Pin) {
        change_wave = 1;
    }
}

/* USER CODE END 0 */

/**
 * @brief  The application entry point.
 * @retval int
 */
int main(void)
{

    /* USER CODE BEGIN 1 */

    /* USER CODE END 1 */

    /* MPU Configuration--------------------------------------------------------*/
    MPU_Config();

    /* Enable the CPU Cache */

    /* Enable I-Cache---------------------------------------------------------*/
    SCB_EnableICache();

    /* MCU Configuration--------------------------------------------------------*/

    /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
    HAL_Init();

    /* USER CODE BEGIN Init */

    /* USER CODE END Init */

    /* Configure the system clock */
    SystemClock_Config();

    /* USER CODE BEGIN SysInit */

    /* USER CODE END SysInit */

    /* Initialize all configured peripherals */
    MX_GPIO_Init();
    MX_DMA_Init();
    MX_I2S2_Init();
    MX_USART1_UART_Init();
    MX_USB_OTG_HS_PCD_Init();
    /* USER CODE BEGIN 2 */

    // Data cache on: the voices are in the DTCM (never cached), the rest of
    // the synth state and the stack in the AXI SRAM run much faster with it.
    // The DMA buffer is cleaned after every block (see the main loop).
    SCB_EnableDCache();

    printf("\n\n\ncmsynth on the STM32H723 (%lu MHz, %d voices)\n", SystemCoreClock / 1000000, MAX_VOICES);

    // UART TX interrupt for the non-blocking printf
    HAL_NVIC_SetPriority(USART1_IRQn, 6, 0);
    HAL_NVIC_EnableIRQ(USART1_IRQn);

    // Enable USB IRQ for TinyUSB event handling
    HAL_NVIC_SetPriority(OTG_HS_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(OTG_HS_IRQn);

    // Enable the DWT cycle counter for CPU load measurement (the M7 needs it unlocked)
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->LAR = 0xC5ACCE55;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    // Cycles available per audio block
    const uint32_t block_budget = SystemCoreClock / SAMPLE_FREQ * SYNTH_BLOCK_SIZE;

    synth_init();
    synth_set_master_volume(0.5f);

#if SYNTH_BENCHMARK
    synth_benchmark(dwt_cycles);
#endif
    synth_init();

    // Start I2S DMA transmission using full buffer size
    SCB_CleanDCache_by_Addr((uint32_t*) i2s_dma_buffer, sizeof(i2s_dma_buffer));
    HAL_I2S_Transmit_DMA(&hi2s2, (uint16_t*) i2s_dma_buffer, I2S_DMA_BUFFER_SIZE);

    // Initialize TinyUSB Device stack
    tusb_init();

    // Soft connect on the OTG_HS peripheral (pulls D+ high via the internal resistor)
    HAL_PCD_DevConnect(&hpcd_USB_OTG_HS);

    /* USER CODE END 2 */

    /* Infinite loop */
    /* USER CODE BEGIN WHILE */

    uint32_t now = 0;
    uint32_t loop_cnt = 0;
    uint32_t next_blink = 500;
    uint32_t next_tick = 1000;

    while (1) {

        // Process audio buffer IMMEDIATELY when requested by ISR
        if (dma_buffer_to_fill != NULL) {
            int16_t *buf = (int16_t*) dma_buffer_to_fill;
            dma_buffer_to_fill = NULL; // Clear flag before processing to prevent double-fills

            uint32_t start = DWT->CYCCNT;
            synth_process(buf);
            uint32_t cycles = DWT->CYCCNT - start;

            // Write the rendered half from the data cache to RAM for the DMA
            SCB_CleanDCache_by_Addr((uint32_t*) buf, I2S_DMA_BUFFER_SIZE / 2 * sizeof(int16_t));

            perf_cycles_sum += cycles;
            if (cycles > perf_cycles_max)
                perf_cycles_max = cycles;
            ++perf_blocks;
        }

        // 2. Handle TinyUSB events
        tud_task();

        // 3. Low priority tasks
        now = uwTick;

        if (change_wave) {
            printf("Ch  1 osc1 wave -> %d\n", synth_next_wave(0));
            change_wave = 0;
        }

        if (now >= next_blink) {
            HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);
            next_blink = now + 500;
        }

        if (now >= next_tick) {
            uint32_t avg = perf_blocks ? perf_cycles_sum / perf_blocks : 0;
            printf("Tick %lu (loop=%lu) voices=%d cpu avg=%lu.%lu%% max=%lu.%lu%% (%lu/%lu cycles) overruns=%lu\n",
                    now / 1000, loop_cnt, synth_active_voices(),
                    avg * 100 / block_budget, (avg * 1000 / block_budget) % 10,
                    perf_cycles_max * 100 / block_budget, (perf_cycles_max * 1000 / block_budget) % 10,
                    perf_cycles_max, block_budget, dma_overruns);
            perf_cycles_sum = perf_cycles_max = perf_blocks = 0;
            loop_cnt = 0;
            next_tick = now + 1000;
        }

        ++loop_cnt;

        /* USER CODE END WHILE */

        /* USER CODE BEGIN 3 */
    }
    /* USER CODE END 3 */
}

/**
 * @brief System Clock Configuration
 * @retval None
 */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = { 0 };
    RCC_ClkInitTypeDef RCC_ClkInitStruct = { 0 };

    /** Supply configuration update enable
     */
    HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);

    /** Configure the main internal regulator output voltage
     */
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE0);

    while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {
    }

    /** Initializes the RCC Oscillators according to the specified parameters
     * in the RCC_OscInitTypeDef structure.
     */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI48 | RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.HSI48State = RCC_HSI48_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 1;
    RCC_OscInitStruct.PLL.PLLN = 34;
    RCC_OscInitStruct.PLL.PLLP = 1;
    RCC_OscInitStruct.PLL.PLLQ = 5;
    RCC_OscInitStruct.PLL.PLLR = 2;
    RCC_OscInitStruct.PLL.PLLRGE = RCC_PLL1VCIRANGE_3;
    RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
    RCC_OscInitStruct.PLL.PLLFRACN = 3072;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
            {
        Error_Handler();
    }

    /** Initializes the CPU, AHB and APB buses clocks
     */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
            | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2
            | RCC_CLOCKTYPE_D3PCLK1 | RCC_CLOCKTYPE_D1PCLK1;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV2;
    RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV2;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;
    RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV2;

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_3) != HAL_OK)
            {
        Error_Handler();
    }
}

/**
 * @brief I2S2 Initialization Function
 * @param None
 * @retval None
 */
static void MX_I2S2_Init(void)
{

    /* USER CODE BEGIN I2S2_Init 0 */

    /* USER CODE END I2S2_Init 0 */

    /* USER CODE BEGIN I2S2_Init 1 */

    /* USER CODE END I2S2_Init 1 */
    hi2s2.Instance = SPI2;
    hi2s2.Init.Mode = I2S_MODE_MASTER_TX;
    hi2s2.Init.Standard = I2S_STANDARD_PHILIPS;
    hi2s2.Init.DataFormat = I2S_DATAFORMAT_16B;
    hi2s2.Init.MCLKOutput = I2S_MCLKOUTPUT_DISABLE;
    hi2s2.Init.AudioFreq = I2S_AUDIOFREQ_48K;
    hi2s2.Init.CPOL = I2S_CPOL_LOW;
    hi2s2.Init.FirstBit = I2S_FIRSTBIT_MSB;
    hi2s2.Init.WSInversion = I2S_WS_INVERSION_DISABLE;
    hi2s2.Init.Data24BitAlignment = I2S_DATA_24BIT_ALIGNMENT_RIGHT;
    hi2s2.Init.MasterKeepIOState = I2S_MASTER_KEEP_IO_STATE_DISABLE;
    if (HAL_I2S_Init(&hi2s2) != HAL_OK)
            {
        Error_Handler();
    }
    /* USER CODE BEGIN I2S2_Init 2 */

    /* USER CODE END I2S2_Init 2 */

}

/**
 * @brief USART1 Initialization Function
 * @param None
 * @retval None
 */
static void MX_USART1_UART_Init(void)
{

    /* USER CODE BEGIN USART1_Init 0 */

    /* USER CODE END USART1_Init 0 */

    /* USER CODE BEGIN USART1_Init 1 */

    /* USER CODE END USART1_Init 1 */
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 921600;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_16;
    huart1.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
    huart1.Init.ClockPrescaler = UART_PRESCALER_DIV1;
    huart1.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
    if (HAL_UART_Init(&huart1) != HAL_OK)
            {
        Error_Handler();
    }
    if (HAL_UARTEx_SetTxFifoThreshold(&huart1, UART_TXFIFO_THRESHOLD_1_8) != HAL_OK)
            {
        Error_Handler();
    }
    if (HAL_UARTEx_SetRxFifoThreshold(&huart1, UART_RXFIFO_THRESHOLD_1_8) != HAL_OK)
            {
        Error_Handler();
    }
    if (HAL_UARTEx_DisableFifoMode(&huart1) != HAL_OK)
            {
        Error_Handler();
    }
    /* USER CODE BEGIN USART1_Init 2 */

    /* USER CODE END USART1_Init 2 */

}

/**
 * @brief USB_OTG_HS Initialization Function
 * @param None
 * @retval None
 */
static void MX_USB_OTG_HS_PCD_Init(void)
{

    /* USER CODE BEGIN USB_OTG_HS_PCD_Init 0 */

    /* USER CODE END USB_OTG_HS_PCD_Init 0 */

    /* USER CODE BEGIN USB_OTG_HS_PCD_Init 1 */

    /* USER CODE END USB_OTG_HS_PCD_Init 1 */
    hpcd_USB_OTG_HS.Instance = USB_OTG_HS;
    hpcd_USB_OTG_HS.Init.dev_endpoints = 9;
    hpcd_USB_OTG_HS.Init.speed = PCD_SPEED_FULL;
    hpcd_USB_OTG_HS.Init.dma_enable = DISABLE;
    hpcd_USB_OTG_HS.Init.phy_itface = USB_OTG_EMBEDDED_PHY;
    hpcd_USB_OTG_HS.Init.Sof_enable = DISABLE;
    hpcd_USB_OTG_HS.Init.low_power_enable = DISABLE;
    hpcd_USB_OTG_HS.Init.lpm_enable = DISABLE;
    hpcd_USB_OTG_HS.Init.vbus_sensing_enable = DISABLE;
    hpcd_USB_OTG_HS.Init.use_dedicated_ep1 = DISABLE;
    hpcd_USB_OTG_HS.Init.use_external_vbus = DISABLE;
    if (HAL_PCD_Init(&hpcd_USB_OTG_HS) != HAL_OK)
            {
        Error_Handler();
    }
    /* USER CODE BEGIN USB_OTG_HS_PCD_Init 2 */

    /* USER CODE END USB_OTG_HS_PCD_Init 2 */

}

/**
 * Enable DMA controller clock
 */
static void MX_DMA_Init(void)
{

    /* DMA controller clock enable */
    __HAL_RCC_DMA1_CLK_ENABLE();

    /* DMA interrupt init */
    /* DMA1_Stream0_IRQn interrupt configuration */
    HAL_NVIC_SetPriority(DMA1_Stream0_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(DMA1_Stream0_IRQn);

}

/**
 * @brief GPIO Initialization Function
 * @param None
 * @retval None
 */
static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = { 0 };
    /* USER CODE BEGIN MX_GPIO_Init_1 */

    /* USER CODE END MX_GPIO_Init_1 */

    /* GPIO Ports Clock Enable */
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOH_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();

    /*Configure GPIO pin Output Level */
    HAL_GPIO_WritePin(LED_GPIO_Port, LED_Pin, GPIO_PIN_SET);

    /*Configure GPIO pin : LED_Pin */
    GPIO_InitStruct.Pin = LED_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_OD;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(LED_GPIO_Port, &GPIO_InitStruct);

    /*Configure GPIO pin : BTN_Pin */
    GPIO_InitStruct.Pin = BTN_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(BTN_GPIO_Port, &GPIO_InitStruct);

    /* EXTI interrupt init*/
    HAL_NVIC_SetPriority(BTN_EXTI_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(BTN_EXTI_IRQn);

    /* USER CODE BEGIN MX_GPIO_Init_2 */

    /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/* MPU Configuration */

void MPU_Config(void)
{
    MPU_Region_InitTypeDef MPU_InitStruct = { 0 };

    /* Disables the MPU */
    HAL_MPU_Disable();

    /** Initializes and configures the Region and the memory to be protected
     */
    MPU_InitStruct.Enable = MPU_REGION_ENABLE;
    MPU_InitStruct.Number = MPU_REGION_NUMBER0;
    MPU_InitStruct.BaseAddress = 0x0;
    MPU_InitStruct.Size = MPU_REGION_SIZE_4GB;
    MPU_InitStruct.SubRegionDisable = 0x87;
    MPU_InitStruct.TypeExtField = MPU_TEX_LEVEL0;
    MPU_InitStruct.AccessPermission = MPU_REGION_NO_ACCESS;
    MPU_InitStruct.DisableExec = MPU_INSTRUCTION_ACCESS_DISABLE;
    MPU_InitStruct.IsShareable = MPU_ACCESS_SHAREABLE;
    MPU_InitStruct.IsCacheable = MPU_ACCESS_NOT_CACHEABLE;
    MPU_InitStruct.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;

    HAL_MPU_ConfigRegion(&MPU_InitStruct);
    /* Enables the MPU */
    HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);

}

/**
 * @brief  This function is executed in case of error occurrence.
 * @retval None
 */
void Error_Handler(void)
{
    /* USER CODE BEGIN Error_Handler_Debug */
    /* User can add his own implementation to report the HAL error return state */
    __disable_irq();
    while (1)
    {
    }
    /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
