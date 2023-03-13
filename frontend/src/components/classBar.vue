<template>
    <div ref="classBarRef" class="chart">
        <!-- <p>{{ fatherDataName }}</p> -->
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref, defineProps, watchEffect } from 'vue';
import * as echarts from 'echarts';
import 'echarts/theme/macarons.js';
import { fetchExcellentBarData } from '../api/index';

const props = defineProps({
    chartData: Object,
});
const classBarRef = ref<HTMLDivElement>()
onMounted(() => {
    watchEffect(()=>{
        console.log('props.chartData:',props.chartData);
        let data = props.chartData;
        let classNameList = data?.classNameList;
        let failedNum = data?.failedNum;
        let failedRate = data?.failedRate;
        // 基于准备好的dom，初始化echarts实例
        var myChart = echarts.init(classBarRef.value as HTMLDivElement, 'macarons');
        var option = {
            tooltip: {
                trigger: 'axis',
                backgroundColor: '#fff',
                axisPointer: {
                    type: 'cross',
                    crossStyle: {
                        color: '#999'
                    }
                }
            },
            toolbox: {
                feature: {
                    dataView: { show: true, readOnly: false },
                    magicType: { show: true, type: ['line', 'bar'] },
                    restore: { show: true },
                    saveAsImage: { show: true }
                }
            },
            grid: {
                top: 100,
            },
            legend: {
                data: ['通过人数', '通过率比例']
            },
            xAxis: [
                {
                    type: 'category',
                    data: classNameList,
                    axisPointer: {
                        type: 'shadow'
                    }
                }
            ],
            yAxis: [
                {
                    type: 'value',
                    name: '通过人数',
                    minInterval: 1,
                    nameTextStyle: {
                        fontSize: '16'
                    },
                    axisLabel: {
                        formatter: '{value} 人'
                    }
                },
                {
                    type: 'value',
                    name: '通过率比例',
                    nameTextStyle: {
                        fontSize: '16'
                    },
                    axisLabel: {
                        formatter: '{value} %'
                    }
                }
            ],
            series: [
                {
                    name: '通过人数',
                    type: 'bar',
                    smooth: false,
                    tooltip: {
                        valueFormatter: function (value: string) {
                            return value + ' 人';
                        }
                    },
                    data: failedNum,
                    itemStyle: {
                        normal: {
                            label: {
                                show: true,
                                position: 'insideBottom',
                                textStyle: {
                                    color: 'black',
                                    fontSize: 12,
                                },
                                formatter: function(realData:any) {
                                    return realData.value+'人'
                                }
                            }
                        }
                    }
                },
                {
                    name: '通过率比例',
                    type: 'line',
                    smooth: false,
                    yAxisIndex: 1,
                    tooltip: {
                        valueFormatter: function (value: string) {
                            return value + ' %';
                        }
                    },
                    data: failedRate,
                    itemStyle: {
                        normal: {
                            label: {
                                show: true,
                                position: 'top',
                                textStyle: {
                                    color: 'black',
                                    fontSize: 12,
                                },
                                formatter: function(realData:any) {
                                    return realData.value+'%'
                                }
                            }
                        }
                    }
                }
            ]
        };
        // 绘制图表
        myChart.setOption(option);
        window.addEventListener('resize', () => {
            myChart.resize()
        })
    })
})
</script>
<style scoped>
.chart {
    width: 100%;
    height: 500px;
}
</style>