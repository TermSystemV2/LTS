<template>
    <div ref="courseBarRef" class="chart">
        <!-- <p>{{ fatherDataName }}</p> -->
    </div>
</template>

<script setup lang="ts">
import { onMounted, watchEffect, ref, defineProps, watch } from 'vue';
import * as echarts from 'echarts';
import 'echarts/theme/macarons.js';
import { fetchExcellentBarData } from '../api/index';

const props = defineProps({
    chartData: Object,
});
const courseBarRef = ref<HTMLDivElement>()
onMounted(() => {
    //深度监听，每查询一次更新一次图表
    watchEffect(()=>{
        let data = props.chartData;
        let failData = data?.failed_nums;
        let passData = data?.pass_rate;
        let grade = []
        let failNum = []
        let passRate = []
        for (var key in failData) {
            grade.push('20'+key + '年')
            failNum.push(failData[key])
        }
        for (var key in passData) {
            passRate.push(passData[key])
        }
        // console.log('grade[]:'+grade);
        // console.log('failNum[]:'+failNum);
        
        // 基于准备好的dom，初始化echarts实例
        var myChart = echarts.init(courseBarRef.value as HTMLDivElement, 'macarons');
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
                },
                left: 'right'
            },
            legend: {
                data: ['挂科人数', '通过率'],
                left: 'center'
            },
            xAxis: [
                {
                    type: 'category',
                    data: grade,
                    axisPointer: {
                        type: 'shadow'
                    }
                }
            ],
            yAxis: [
                {
                    type: 'value',
                    name: '个数',
                    minInterval: 1,
                    axisLabel: {
                        formatter: '{value} 个'
                    }
                },
                {
                    type: 'value',
                    name: '比例',
                    axisLabel: {
                        formatter: '{value} %'
                    }
                }
            ],
            series: [
                {
                    name: '挂科人数',
                    type: 'bar',
                    smooth: false,
                    tooltip: {
                        valueFormatter: function (value: string) {
                            return value + ' 个';
                        }
                    },
                    data: failNum,
                    itemStyle: {
                        normal: {
                            label: {
                                show: true,
                                position: 'inside',
                                textStyle: {
                                    color: 'black',
                                    fontSize: 12,
                                },
                                formatter: function(realData:any) {
                                    return '个数:'+realData.value
                                }
                            }
                        }
                    }
                },
                {
                    name: '通过率',
                    type: 'line',
                    smooth: false,
                    yAxisIndex: 1,
                    tooltip: {
                        valueFormatter: function (value: string) {
                            return value + ' %';
                        }
                    },
                    data: passRate,
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
                                    return '通过率:'+realData.value+'%'
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